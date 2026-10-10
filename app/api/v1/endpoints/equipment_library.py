"""Read-only API for the source-backed 2026 equipment catalog."""
import json
import re
import sqlite3
import mimetypes
import hashlib
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.equipment_library import (BACKEND_CATALOG_DIR, SOURCE_ROOT, DB_PATH, asset_available,
                                             asset_bytes, catalog_manifest, get_equipment,
                                             search_equipment)

router = APIRouter()

@router.get('/browser-data')
def catalogtb_browser_data():
    from app.services.catalogtb_browser import browser_data
    return browser_data()

@router.get('/projection-catalog')
def projection_catalog():
    """Private catalog used by the CAD ribbon; router entitlement applies."""
    # CatalogTB is the sole source. Unknown dimensions are never guessed.
    from app.services.catalogtb_browser import browser_data
    rows=browser_data()['items']
    return {'brands':sorted({p['brand'] for p in rows if p.get('brand')}),
            'items':[{'ma':p['product_code'],'n':p['display'],'brand':p['brand'],
                      't':p['type'],'w':p['size']['ngang'],'h':p['size']['cao']}
                     for p in rows if p.get('product_code') and p.get('size') and p['size'].get('ngang') and p['size'].get('cao')]}

def _public_record(value):
    if isinstance(value, dict):
        return {key: _public_record(item) for key, item in value.items()
                if key not in {'path', 'source_file', 'profile_path', 'path_base'}}
    if isinstance(value, list):
        return [_public_record(item) for item in value]
    return value


def _natural(value: str):
    return [(0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r'(\d+)', value or '')]


@lru_cache(maxsize=1)
def _source_index_summary() -> dict:
    """Read only the supplied index page for its published catalog totals."""
    index_path = SOURCE_ROOT / 'index_2026.html'
    if not index_path.is_file():
        index_path = BACKEND_CATALOG_DIR / 'source_index_2026.html'
    if not index_path.is_file():
        return {}
    content = index_path.read_text(encoding='utf-8')
    measurement = re.search(
        r'<h2>Đồng hồ và đo lường</h2>.*?<strong>(\d+) thiết bị</strong>.*?'
        r'href="THIET_BI_KHAC_2026/do_luong\.html"', content, re.DOTALL
    )
    return {
        'price_rows': sum(map(int, re.findall(r'<strong>(\d+) dòng</strong>', content))),
        'price_rows_with_linked_cad': sum(map(int, re.findall(
            r'<small>(\d+) dòng có CAD đã ghép</small>', content))),
        'source_cad_devices': sum(map(int, re.findall(r'<strong>(\d+) thiết bị</strong>', content))),
        'measurement_cad_devices': int(measurement.group(1)) if measurement else 0,
    }


def _category_matches(row: dict, selected: str) -> bool:
    if row.get('category') == selected:
        return True
    # The 2026 index lists measurement CAD as one section; price PDF headings
    # split it into several groups. These are related drawings, not SKU matches.
    if (row.get('record_type') != 'source_cad_device_or_assembly'
            or row.get('category') != 'do_luong'
            or not _source_index_summary().get('measurement_cad_devices')):
        return False
    return selected == 'Đo lường và giám sát' or selected.startswith(
        'Đồng hồ điện đa năng kỹ thuật số'
    )


@lru_cache(maxsize=1)
def _manufacturer_links():
    path = BACKEND_CATALOG_DIR / 'source_manufacturer_cad_links.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


@lru_cache(maxsize=1)
def _manufacturer_views():
    path = BACKEND_CATALOG_DIR / 'manufacturer_cad_views.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def _record_views(record):
    source_id = record['cad'].get('source_id')
    if record['record_type'] == 'priced_variant' and source_id in _manufacturer_views():
        return _manufacturer_views()[source_id]
    return record['cad'].get('views', [])


def _linked_group_key(row):
    """Only group source views with the same identified brand, model and frame CAD."""
    if row['record_type'] != 'source_cad_device_or_assembly':
        return None
    link = _manufacturer_links().get(row['catalog_id'])
    if not link:
        return None
    return (row['brand'], row['category'], row['model'].casefold().strip(), link['catalog_id'])


def _linked_group(row):
    key = _linked_group_key(row)
    if not key:
        return [row]
    with sqlite3.connect(DB_PATH) as db:
        candidates = [json.loads(result[0]) for result in db.execute(
            "SELECT record_json FROM equipment WHERE record_type = 'source_cad_device_or_assembly' AND brand = ? AND category = ? AND lower(model) = ?",
            (row['brand'], row['category'], row['model'].casefold()))]
    return sorted((candidate for candidate in candidates if _linked_group_key(candidate) == key),
                  key=lambda candidate: candidate['catalog_id'])


@router.get('/browse')
def browse(q: str = '', category: str = '', brand: str = '',
           cad: str = 'all', record_type: str = 'all',
           poles: int | None = None, min_in: float | None = None,
           max_in: float | None = None, min_icu: float | None = None,
           skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    """Browse every source-backed 2026 price row and CAD source record."""
    if cad not in ('all', 'yes', 'no'):
        raise HTTPException(422, 'Bộ lọc không hợp lệ.')
    if record_type not in ('all', 'priced_variant', 'source_cad_device_or_assembly'):
        raise HTTPException(422, 'Loại bản ghi không hợp lệ.')
    if not DB_PATH.is_file():
        raise HTTPException(503, 'Chưa có catalog thiết bị 2026.')
    with sqlite3.connect(DB_PATH) as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT record_json FROM equipment')]
    source_count = sum(row['record_type'] == 'source_cad_device_or_assembly' for row in rows)
    price_count = sum(row['record_type'] == 'priced_variant' for row in rows)
    if record_type != 'all':
        rows = [row for row in rows if row['record_type'] == record_type]
    categories = sorted({row['category'] for row in rows if row.get('category')}, key=_natural)
    brands = sorted({row['brand'] for row in rows if row.get('brand')}, key=_natural)
    if category:
        rows = [row for row in rows if _category_matches(row, category)]
    if brand:
        rows = [row for row in rows if row.get('brand') == brand]
    if q.strip():
        terms = q.casefold().split()
        def search_text(row):
            values = [row.get(key) for key in
                      ('catalog_id', 'model', 'material_code', 'display_name', 'category', 'brand', 'description')]
            values.append(row['specifications'].get('current_display'))
            return ' '.join(str(value or '') for value in values).casefold()
        rows = [row for row in rows if all(term in search_text(row) for term in terms)]
    if poles is not None:
        rows = [row for row in rows if row['specifications'].get('poles') == poles]
    if min_in is not None or max_in is not None:
        def current_matches(row):
            value = row['specifications'].get('current_a')
            if value is None:
                return True  # Family candidate, not an exact rating match.
            try:
                current = float(value)
            except (TypeError, ValueError):
                return False
            return (min_in is None or current >= min_in) and (max_in is None or current <= max_in)
        rows = [row for row in rows if current_matches(row)]
    if min_icu is not None:
        def icu_matches(row):
            value = row['specifications'].get('breaking_capacity_ka')
            match = re.search(r'\d+(?:[.,]\d+)?', str(value or ''))
            return bool(match and float(match.group().replace(',', '.')) >= min_icu)
        rows = [row for row in rows if icu_matches(row)]
    if cad != 'all':
        rows = [row for row in rows if any(ref and asset_available(ref['path'])
                for ref in (row['cad'].get('preview'), row['cad'].get('dxf'))) == (cad == 'yes')]
    rows.sort(key=lambda row: (
        _natural(row.get('category') or ''), _natural(row.get('brand') or ''),
        _natural(row.get('model') or row['display_name']), _natural(row['catalog_id'])))
    seen_groups = set()
    grouped_rows = []
    for row in rows:
        group = _linked_group_key(row)
        if group and group in seen_groups:
            continue
        if group:
            seen_groups.add(group)
        grouped_rows.append(row)
    rows = grouped_rows
    total = len(rows)
    return {'items': [{
        'catalog_id': row['catalog_id'], 'name': row['display_name'], 'model': row['model'],
        'material_code': row.get('material_code'), 'source_record': row.get('source_record'),
        'brand': row['brand'], 'category': row['category'], 'record_type': row['record_type'],
        'cad_status': row['cad']['status'], 'has_preview': bool(row['cad'].get('preview') and
            asset_available(row['cad']['preview']['path'])),
        'has_dxf': bool(row['cad'].get('dxf') and asset_available(row['cad']['dxf']['path'])),
        'display_preview_catalog_id': (_manufacturer_links().get(row['catalog_id']) or {}).get('catalog_id'),
        'display_preview_basis': (_manufacturer_links().get(row['catalog_id']) or {}).get('match_basis'),
        'price_vnd': (row.get('price') or {}).get('amount_vnd'),
        'poles': row['specifications'].get('poles'),
        'current_a': row['specifications'].get('current_a'),
        'current_display': row['specifications'].get('current_display'),
        'breaking_capacity_ka': row['specifications'].get('breaking_capacity_ka'),
        'rating_complete': all(row['specifications'].get(key) is not None
                               for key in ('poles', 'current_a', 'breaking_capacity_ka')),
    } for row in rows[skip:skip + limit]], 'total': total,
        'categories': categories, 'brands': brands, 'source_count': source_count,
        'price_count': price_count, 'source_index': _source_index_summary()}


def _cad_file(catalog_id: str, field: str):
    record = get_equipment(catalog_id)
    if not record or not record['cad'].get(field):
        raise HTTPException(404, 'Bản CAD này chưa có file.')
    relative = record['cad'][field]['path']
    if not asset_available(relative):
        raise HTTPException(404, 'Không tìm thấy file CAD nguồn.')
    return relative


@router.get('/{catalog_id}/drawing-source')
def drawing_source(catalog_id: str):
    record = get_equipment(catalog_id)
    if not record or not record.get('drawing_analysis'):
        raise HTTPException(404, 'Không có ảnh bản vẽ đã phân tích cho thiết bị này.')
    path = BACKEND_CATALOG_DIR / 'identified_meters' / 'source_drawing.png'
    if not path.is_file():
        raise HTTPException(404, 'Không tìm thấy ảnh bản vẽ nguồn.')
    return Response(path.read_bytes(), media_type='image/png')


def _cad_view_file(catalog_id: str, view_id: str, field: str):
    record = get_equipment(catalog_id)
    views = _record_views(record) if record else []
    view = next((view for view in views if view.get('id') == view_id), None)
    if not view or not view.get(field):
        raise HTTPException(404, 'Góc nhìn CAD này chưa có file.')
    relative = view[field]['path']
    if not asset_available(relative):
        raise HTTPException(404, 'Không tìm thấy góc nhìn CAD nguồn.')
    return relative


@router.get('/{catalog_id}/preview')
def preview(catalog_id: str):
    relative = _cad_file(catalog_id, 'preview')
    return _preview_response(relative)

def _raster_preview(relative: str) -> bytes:
    # A repaired SVG at the same path must invalidate the old raster image.
    return _raster_preview_source(asset_bytes(relative))


@lru_cache(maxsize=128)
def _raster_preview_source(source: bytes) -> bytes:
    import cairosvg
    from xml.etree import ElementTree
    svg = ElementTree.fromstring(source)
    bounds = [float(part) for part in svg.attrib.get('viewBox', '0 0 1000 1000').replace(',', ' ').split()]
    width, height = max(bounds[2], 1), max(bounds[3], 1)
    scale = 1400 / max(width, height)
    return cairosvg.svg2png(bytestring=source, output_width=max(1, round(width*scale)),
                           output_height=max(1, round(height*scale)))

def _preview_response(relative: str):
    if relative.lower().endswith('.svg'):
        return Response(_raster_preview(relative), media_type='image/png')
    return Response(asset_bytes(relative), media_type=mimetypes.guess_type(relative)[0] or 'image/png')


@router.get('/{catalog_id}/dxf')
def download_dxf(catalog_id: str):
    return Response(asset_bytes(_cad_file(catalog_id, 'dxf')), media_type='application/dxf',
                    headers={'Content-Disposition': f'attachment; filename="{catalog_id}.dxf"'})


@router.get('/{catalog_id}/dwg')
def download_dwg(catalog_id: str):
    return Response(asset_bytes(_cad_file(catalog_id, 'dwg')), media_type='application/acad',
                    headers={'Content-Disposition': f'attachment; filename="{catalog_id}.dwg"'})


@router.get('/{catalog_id}/views/{view_id}/preview')
def view_preview(catalog_id: str, view_id: str):
    relative = _cad_view_file(catalog_id, view_id, 'preview')
    return _preview_response(relative)


@router.get('/{catalog_id}/views/{view_id}/dxf')
def view_dxf(catalog_id: str, view_id: str):
    relative = _cad_view_file(catalog_id, view_id, 'dxf')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', f'{catalog_id}-{view_id}.dxf')
    return Response(asset_bytes(relative), media_type='application/dxf',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.get('/{catalog_id}/views/{view_id}/dwg')
def view_dwg(catalog_id: str, view_id: str):
    relative = _cad_view_file(catalog_id, view_id, 'dwg')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', f'{catalog_id}-{view_id}.dwg')
    return Response(asset_bytes(relative), media_type='application/acad',
                    headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@router.get('/manifest')
def manifest():
    try:
        return catalog_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get('/search')
def search(q: str = '', brand: str | None = None, cad_status: str | None = None,
           limit: int = Query(20, ge=1, le=100)):
    try:
        return {'path_base': 'BE_AIDE/data/CatalogTB',
                'items': search_equipment(q, brand, cad_status, limit)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get('/{catalog_id}')
def detail(catalog_id: str):
    try:
        item = get_equipment(catalog_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail='Equipment record not found')
    if item['record_type'] == 'priced_variant':
        item['cad']['views'] = [
            {**view, 'state': view['name'],
             **{field: {**view[field], 'available_now': asset_available(view[field]['path'])}
                for field in ('preview', 'dxf', 'dwg')}}
            for view in _record_views(item)]
        item['cad']['default_view_id'] = item['cad'].get('state_id')
    group = _linked_group(item)
    link = _manufacturer_links().get(catalog_id)
    if link:
        manufacturer = get_equipment(link['catalog_id'])
        item['manufacturer_frame_cad'] = {
            'catalog_id': manufacturer['catalog_id'],
            'model_on_drawing': link['model_on_drawing'],
            'match_basis': link['match_basis'],
        }
        views = []
        if (manufacturer['cad'].get('preview') or {}).get('available_now'):
            views.append({'id': f"manufacturer:{manufacturer['catalog_id']}",
                          'name': 'CAD gốc của hãng', 'state': 'Mặt trước theo khung',
                          'preview_catalog_id': manufacturer['catalog_id'],
                          'dxf_catalog_id': manufacturer['catalog_id'] if (manufacturer['cad'].get('dxf') or {}).get('available_now') else None,
                          'dwg_catalog_id': manufacturer['catalog_id'] if (manufacturer['cad'].get('dwg') or {}).get('available_now') else None,
                          'preview': manufacturer['cad']['preview'], 'dxf': manufacturer['cad'].get('dxf'),
                          'dwg': manufacturer['cad'].get('dwg')})
        seen_previews = set()
        for member in group:
            face = (_manufacturer_links().get(member['catalog_id']) or {}).get('source_face_label')
            for view in member['cad'].get('views', []):
                preview = view.get('preview')
                if preview and asset_available(preview['path']):
                    digest = hashlib.sha256(asset_bytes(preview['path'])).digest()
                    if digest in seen_previews:
                        continue
                    seen_previews.add(digest)
                enriched = dict(view)
                enriched['record_id'] = member['catalog_id']
                enriched['state'] = face or f'CAD nguồn {len(seen_previews)}'
                for field in ('preview', 'dxf'):
                    if enriched.get(field):
                        enriched[field] = {**enriched[field], 'available_now': asset_available(enriched[field]['path'])}
                views.append(enriched)
        item['cad']['views'] = views
        item['grouped_source_ids'] = [member['catalog_id'] for member in group]
    return _public_record(item)

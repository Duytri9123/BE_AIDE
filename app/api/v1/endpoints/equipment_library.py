"""Read-only API for the source-backed 2026 equipment catalog."""
import json
import re
import sqlite3
import mimetypes
import hashlib
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.equipment_library import (BACKEND_CATALOG_DIR, DB_PATH, asset_available,
                                             asset_bytes, catalog_manifest, get_equipment,
                                             search_equipment)

router = APIRouter()


def _natural(value: str):
    return [(0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r'(\d+)', value or '')]


@lru_cache(maxsize=1)
def _manufacturer_links():
    path = BACKEND_CATALOG_DIR / 'source_manufacturer_cad_links.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


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
        rows = [row for row in rows if row.get('category') == category]
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
    } for row in rows[skip:skip + limit]], 'total': total,
        'categories': categories, 'brands': brands, 'source_count': source_count,
        'price_count': price_count}


def _cad_file(catalog_id: str, field: str):
    record = get_equipment(catalog_id)
    if not record or not record['cad'].get(field):
        raise HTTPException(404, 'Bản CAD này chưa có file.')
    relative = record['cad'][field]['path']
    if not asset_available(relative):
        raise HTTPException(404, 'Không tìm thấy file CAD nguồn.')
    return relative


def _cad_view_file(catalog_id: str, view_id: str, field: str):
    record = get_equipment(catalog_id)
    view = next((view for view in (record or {}).get('cad', {}).get('views', [])
                 if view.get('id') == view_id), None)
    if not view or not view.get(field):
        raise HTTPException(404, 'Góc nhìn CAD này chưa có file.')
    relative = view[field]['path']
    if not asset_available(relative):
        raise HTTPException(404, 'Không tìm thấy góc nhìn CAD nguồn.')
    return relative


@router.get('/{catalog_id}/preview')
def preview(catalog_id: str):
    relative = _cad_file(catalog_id, 'preview')
    return Response(asset_bytes(relative), media_type=mimetypes.guess_type(relative)[0] or 'image/svg+xml')


@router.get('/{catalog_id}/dxf')
def download_dxf(catalog_id: str):
    return Response(asset_bytes(_cad_file(catalog_id, 'dxf')), media_type='application/dxf',
                    headers={'Content-Disposition': f'attachment; filename="{catalog_id}.dxf"'})


@router.get('/{catalog_id}/views/{view_id}/preview')
def view_preview(catalog_id: str, view_id: str):
    relative = _cad_view_file(catalog_id, view_id, 'preview')
    return Response(asset_bytes(relative), media_type=mimetypes.guess_type(relative)[0] or 'image/svg+xml')


@router.get('/{catalog_id}/views/{view_id}/dxf')
def view_dxf(catalog_id: str, view_id: str):
    relative = _cad_view_file(catalog_id, view_id, 'dxf')
    filename = re.sub(r'[^A-Za-z0-9._-]', '_', f'{catalog_id}-{view_id}.dxf')
    return Response(asset_bytes(relative), media_type='application/dxf',
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
        return {'path_base': 'Tudien/CATALOG_PHU_KIEN_DOC_LAP',
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
                          'preview': manufacturer['cad']['preview'], 'dxf': manufacturer['cad'].get('dxf')})
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
    return item

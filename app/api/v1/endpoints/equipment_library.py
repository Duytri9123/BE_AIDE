"""Read-only API for the source-backed 2026 equipment catalog."""
import json
import re
import sqlite3
import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from app.services.equipment_library import DB_PATH, asset_available, asset_bytes, catalog_manifest, get_equipment, search_equipment

router = APIRouter()


def _natural(value: str):
    return [(0, int(part)) if part.isdigit() else (1, part.casefold())
            for part in re.split(r'(\d+)', value or '')]


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
    total = len(rows)
    return {'items': [{
        'catalog_id': row['catalog_id'], 'name': row['display_name'], 'model': row['model'],
        'brand': row['brand'], 'category': row['category'], 'record_type': row['record_type'],
        'cad_status': row['cad']['status'], 'has_preview': bool(row['cad'].get('preview') and
            asset_available(row['cad']['preview']['path'])),
        'has_dxf': bool(row['cad'].get('dxf') and asset_available(row['cad']['dxf']['path'])),
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
    return item

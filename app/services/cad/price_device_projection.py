"""Projection choices reachable only through an explicitly linked commercial row."""
from functools import lru_cache
from pathlib import Path
import hashlib
import gzip
import json
import os
import uuid

from app.services.price_row_cad_detail import price_row_detail
from app.services.customer_equipment_information import public_view_id
from app.services.equipment_library import get_equipment, _catalogtb_asset, CATALOG_TB_ROOT
from .catalogtb_assets import face_code
from .device_projection import visible_projection
from .device_block_package import block_package


@lru_cache(maxsize=32)
def _projection(path, stamp):
    cache = Path(__file__).resolve().parents[3] / 'data' / 'device_block_geometry'
    cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(f'{path}:{stamp}:visible-v2'.encode()).hexdigest()
    stored = cache / (key + '.json')
    if (cache / (key + '.failure.json')).is_file():
        raise ValueError('Mặt CAD cần kiểm tra nguồn; mở DXF gốc trong CAD Viewer.')
    compressed=stored.with_suffix('.json.gz')
    if compressed.is_file():
        try:
            with gzip.open(compressed,'rt',encoding='utf8') as stream:return json.load(stream)
        except (OSError,ValueError):pass
    if stored.is_file():
        try:
            return json.loads(stored.read_text(encoding='utf8'))
        except (OSError, ValueError):
            pass
    data = visible_projection(Path(path), CATALOG_TB_ROOT)
    result = {k: v for k, v in data.items() if k != 'source'}
    temporary = cache / (key + '.' + uuid.uuid4().hex + '.tmp')
    payload=json.dumps(result,separators=(',',':'))
    if len(payload)>1000000:
        with gzip.open(temporary,'wt',encoding='utf8') as stream:stream.write(payload)
        os.replace(temporary,compressed)
    else:
        temporary.write_text(payload,encoding='utf8');os.replace(temporary,stored)
    return result


def price_device_projections(public_id, rows, devices):
    detail = price_row_detail(public_id, rows, devices)
    if detail is None:
        raise ValueError('Không tìm thấy dòng báo giá đã chọn.')
    candidates = []
    for linked in detail['cad_devices']:
        record = get_equipment(linked['id'])
        if not record:
            continue
        allowed = {v['id'] for v in linked['views']}
        views = {}
        for view in record['cad']['views']:
            if public_view_id(view['id']) not in allowed:
                continue
            face = face_code(view.get('name') or view.get('state'))
            path = _catalogtb_asset((view.get('dxf') or {}).get('path', ''))
            if path and face not in ('unknown','isometric'):
                try:
                    geometry = _projection(str(path), path.stat().st_mtime_ns)
                except (ValueError, OSError):
                    continue
                views.setdefault(face, []).append({**geometry, 'view_id': public_view_id(view['id']), 'face':face, 'label':view.get('name') or view.get('state') or face})
        for front in views.get('front', []):
            side = views.get('side', [None])[0] if len(views.get('side', [])) == 1 else None
            warnings = []
            if side and abs(front['height']-side['height']) > max(2, front['height']*.05):
                side = None
                warnings.append('Các mặt chưa khớp chiều cao; giữ mặt trước, chưa suy chiều sâu.')
            if not side:
                warnings.append('Chưa có một mặt bên khớp duy nhất; chiều sâu chưa xác nhận.')
            review = record.get('installation_review') or {}
            candidates.append(dict(id=linked['selection_id']+':'+front['view_id'], name=detail['product'].get('sku') or linked['display'],
                model_code=detail['product'].get('sku'), price_row_id=public_id, product=detail['product'],
                width=front['width'], height=front['height'], depth=side['width'] if side else 0,
                front=front, side=side or {'paths': []}, top=views.get('top',[None])[0] if len(views.get('top',[]))==1 else None,
                projections=[v for group in views.values() for v in group], geometry_status='source_cad',
                projectionOnly=not bool(side),
                panel_device=review.get('category') in {'PUSHBUTTON','BUTTON','METER','LIGHT','INDICATOR','SELECTOR','HMI'},
                installation_review=review, warnings=warnings, profile='Dòng báo giá '+public_id,
                link_scope=linked['link_scope']))
    return block_package(detail['product'], candidates)

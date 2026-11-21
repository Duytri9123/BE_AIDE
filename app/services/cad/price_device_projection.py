"""Projection choices reachable only through an explicitly linked commercial row."""
from functools import lru_cache
from pathlib import Path

from app.services.price_row_cad_detail import price_row_detail
from app.services.customer_equipment_information import public_view_id
from app.services.equipment_library import get_equipment, _catalogtb_asset, CATALOG_TB_ROOT
from .catalogtb_assets import face_code
from .device_projection import visible_projection


@lru_cache(maxsize=256)
def _projection(path, stamp):
    data = visible_projection(Path(path), CATALOG_TB_ROOT)
    return {k: v for k, v in data.items() if k != 'source'}


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
            if path and face in ('front', 'side', 'top'):
                try:
                    geometry = _projection(str(path), path.stat().st_mtime_ns)
                except (ValueError, OSError):
                    continue
                views.setdefault(face, []).append({**geometry, 'view_id': public_view_id(view['id'])})
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
                front=front, side=side or {'paths': []}, projectionOnly=not bool(side),
                panel_device=review.get('category') in {'PUSHBUTTON','BUTTON','METER','LIGHT','INDICATOR','SELECTOR','HMI'},
                installation_review=review, warnings=warnings, profile='Dòng báo giá '+public_id,
                link_scope=linked['link_scope']))
    return {'product': detail['product'], 'candidates': candidates}

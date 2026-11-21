"""Restore only named mounting supports referenced by a cabinet's original JSON.

The source sheet has many views. Match each occurrence to the EQUIPMENT bounds,
not the overall sheet, and retain all placement/geometry provenance for reuse.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import ezdxf

from . import cabinet_templates
from .device_projection import visible_entity_projection


@lru_cache(maxsize=8)
def _drawing(path, stamp):
    return ezdxf.readfile(path)


def source_supports(template_id, source_override=None):
    item = cabinet_templates.resolve(template_id)
    root = cabinet_templates.LIBRARY
    layout_path = root / item['layout_analysis_json']
    layout = json.loads(layout_path.read_text(encoding='utf8'))
    source = Path(source_override or item['original_dxf'])
    if not source.is_absolute():
        source = Path(__file__).resolve().parents[4] / source
    source = source.resolve()
    provenance = dict(layout_json=layout_path.relative_to(root).as_posix(),
                      layout_sha256=hashlib.sha256(layout_path.read_bytes()).hexdigest(),
                      source_cad=str(source), coordinate_system='face_local_mm_bottom_left')
    if not source.is_file():
        cache = root.parents[1] / 'cabinet_mechanics' / (template_id + '.json')
        if cache.is_file():
            saved = json.loads(cache.read_text(encoding='utf8'))
            if saved.get('provenance', {}).get('layout_sha256') == provenance['layout_sha256']:
                return {**saved, 'geometry_source': 'cached_source_projection'}
        return dict(items=[], provenance=provenance, warnings=['Không tìm thấy CAD gốc chứa hình đố.'])
    drawing = _drawing(str(source), source.stat().st_mtime_ns)
    if drawing.units != 4:
        raise ValueError('CAD gốc của đố chưa xác nhận đơn vị mm.')
    provenance['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    face = next(f for f in item['faces'] if f['kind'] == 'mounting_plate')
    x0, y0, x1, y1 = face['source_bounds']
    items, warnings = [], []
    for row in layout['layout_occurrences']:
        name = row['block_name']
        if not name.lower().startswith(('base ', 'strut ', 'đố ', 'do ga ')):
            continue
        ix, iy = row['insertion_point_source'][:2]
        if not (x0 <= ix <= x1 and y0 <= iy <= y1):
            continue
        entity = drawing.entitydb.get(row['source_handle'])
        if entity is None or entity.dxftype() != 'INSERT':
            warnings.append(f"Không tìm thấy block đố {row['source_handle']} trong nguồn.")
            continue
        scale = [entity.dxf.xscale, entity.dxf.yscale, entity.dxf.zscale]
        if ((entity.dxf.insert - ezdxf.math.Vec3(row['insertion_point_source'])).magnitude > .01
                or abs(entity.dxf.rotation - row['rotation_deg']) > .01
                or any(abs(a-b) > 1e-6 for a, b in zip(scale, row['scale']))):
            raise ValueError('CAD và JSON gốc không khớp phép đặt đố.')
        geometry = visible_entity_projection(drawing, [entity])
        ox, oy = geometry['origin_mm']
        items.append(dict(id='SRC-' + row['source_handle'], name=name, face_id=face['id'],
                          x=round(ox-x0, 5), y=round(oy-y0, 5), width=geometry['width'], height=geometry['height'],
                          paths=geometry['paths'], thickness=1.5 if '1.5' in name else item['sheet_thickness_mm'],
                          standoff=20, depth_basis='project_preview_value_not_source_verified',
                          source={**provenance, **row}, geometry_status='source_visible_projection_depth_provisional'))
    return dict(items=items, provenance=provenance, warnings=warnings)

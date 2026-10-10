"""Read millimetre mounting envelopes from the explicitly selected source CAD."""
import json
import math
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=256)
def _visible_bounds(path, modified_ns, file_size):
    """Visible CAD envelope, excluding hidden entities and frozen/off layers.

    This is a view envelope, not a manufacturer mounting or terminal map.
    Dynamic source blocks can contain invisible alternative views which must
    not move the insertion anchor or inflate the collision envelope.
    """
    import ezdxf
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.recorder import Recorder
    source = ezdxf.readfile(path)
    if source.units != 4:
        raise ValueError('CAD nguồn chưa xác nhận đơn vị mm.')
    recorder = Recorder()
    Frontend(RenderContext(source), recorder).draw_layout(source.modelspace(), finalize=True)
    bounds = recorder.player().bbox()
    if not bounds.has_data:
        raise ValueError('CAD nguồn không có hình học hiển thị để bố trí.')
    return bounds.extmin.x, bounds.extmin.y, bounds.extmax.x, bounds.extmax.y


def visible_geometry_bounds(path):
    from .catalogtb_assets import insertion_source
    path = insertion_source(path)
    stat = path.stat()
    return _visible_bounds(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def placement_bounds(asset, *, require_mounting=False):
    path = Path(asset['path']).with_name('thong_tin_cad_chen.json')
    metadata = json.loads(path.read_text(encoding='utf8'))
    geometry = metadata.get('hinh_hoc_lap_dat') or {}
    if not geometry and not require_mounting:
        return visible_geometry_bounds(asset['path'])
    if geometry.get('don_vi') != 'mm':
        raise ValueError('CAD nguồn chưa xác nhận đơn vị mm.')
    bounds = geometry.get('bao_hinh_mm') or {}
    width = float(bounds['max_x']) - float(bounds['min_x'])
    height = float(bounds['max_y']) - float(bounds['min_y'])
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError('CAD nguồn có bao hình lắp đặt không hợp lệ.')
    return float(bounds['min_x']), float(bounds['min_y']), float(bounds['max_x']), float(bounds['max_y'])


def _bounds(asset, *, require_mounting=False):
    left,bottom,right,top = placement_bounds(asset, require_mounting=require_mounting)
    return right-left,top-bottom


def selected_envelope(device):
    asset_id = (device.get('cad') or {}).get('asset_id')
    if not str(asset_id or '').startswith('tb:'):
        return None
    from app.services.cad.catalogtb_assets import assets, resolve
    front = resolve(asset_id, 'front')
    width, height = _bounds(front, require_mounting=True)
    sides = [a for a in assets() if a['family_id'] == front['family_id'] and a['face'] == 'side' and a['placement'].get('cho_phep_chen') is not False]
    if len(sides) != 1:
        raise ValueError(f"{device.get('tag') or front['name']}: cần một mặt bên CAD để xác nhận chiều sâu.")
    depth, side_height = _bounds(sides[0], require_mounting=True)
    if abs(height - side_height) > max(2, height * .05):
        raise ValueError('Bao hình mặt trước/mặt bên CAD chưa đồng nhất; cần đối chiếu tư thế lắp.')
    return width, height, depth

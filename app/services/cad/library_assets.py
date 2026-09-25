"""Place explicit library geometry in a generated drawing, without inventing views."""
from ezdxf import bbox
from ezdxf.addons import Importer
import ezdxf


def insert_library_asset(space, asset_id, x, y, rotation=0):
    from app.api.v1.endpoints.cad_library import download_layout
    name = 'LIBRARY_' + asset_id
    doc = space.doc
    if name not in doc.blocks:
        source = ezdxf.readfile(download_layout(asset_id).path)
        block = doc.blocks.new(name)
        importer = Importer(source, doc)
        importer.import_entities(source.modelspace(), target_layout=block)
        importer.finalize()
    block = doc.blocks[name]
    bounds = bbox.extents(block)
    if not bounds.has_data:
        raise ValueError('CAD nguồn không có hình học để chèn')
    ref = space.add_blockref(name, (0, 0), dxfattribs={'rotation': rotation})
    placed = bbox.extents([ref])
    if placed.has_data:
        ref.translate(x - placed.extmin.x, y - placed.extmin.y, 0)
    return bounds.size.x, bounds.size.y


def requested_asset(device, side=False):
    cad = device.get('cad') or (device.get('parameters') or {}).get('cad') or {}
    if not cad:
        return False, None
    from app.api.v1.endpoints.cad_library import manifest
    from app.services.cad.device_families import build_families
    requested = cad.get('asset_id')
    family = next((f for f in build_families(manifest()['items']) if requested in f['asset_ids']), None)
    if family is None:
        raise ValueError('CAD chưa được nhận dạng là một thiết bị để bố trí tủ')
    face = 'side' if side else 'front'
    match = next((v['asset_id'] for v in family['views'] if v['face'] == face), None)
    if not match and not side:
        raise ValueError('CAD chưa xác nhận mặt trước; không tự dùng hình nguồn hoặc mặt cắt thay thế')
    return True, match

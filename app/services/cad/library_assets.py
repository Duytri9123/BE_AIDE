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
    space.add_blockref(name, (x, y), dxfattribs={'rotation': rotation})
    return bounds.size.x, bounds.size.y


def requested_asset(device, side=False):
    cad = device.get('cad') or (device.get('parameters') or {}).get('cad') or {}
    if not cad:
        return False, None
    views = cad.get('views') or {}
    return True, views.get('side' if side else 'front') or (None if side else cad.get('asset_id'))

"""Place explicit library geometry in a generated drawing, without inventing views."""
from ezdxf import bbox
from ezdxf.addons import Importer
import ezdxf
import re
import unicodedata
import math


def _normal(value):
    value = ''.join(c for c in unicodedata.normalize('NFD', str(value or '').upper()) if not unicodedata.combining(c))
    return value.replace('Đ', 'D')


def _exact_catalog_asset(device, families):
    """Resolve only a unique, SKU-identified front view from the source library."""
    sku = _normal(device.get('part_number')).strip()
    if len(sku) < 5:
        return None
    brand = _normal(device.get('brand')).strip()
    category = _normal(device.get('category')).strip()
    matches = []
    for family in families:
        if (family.get('recognition') or {}).get('status') == 'reference_geometry':
            continue
        if family.get('kind') != 'device':
            continue
        fronts = [view['asset_id'] for view in family['views'] if view['face'] == 'front']
        if len(fronts) != 1:
            continue
        description = _normal(' '.join([family['name'], *(family.get('recognition') or {}).get('texts', [])]))
        if not re.search(r'(?<![A-Z0-9])' + re.escape(sku) + r'(?![A-Z0-9])', description):
            continue
        family_brand = _normal(family.get('brand'))
        if brand and brand not in family_brand and brand not in description:
            continue
        if category in ('ACB', 'MCCB', 'MCB', 'VSD', 'SPD', 'CONTACTOR') and category not in description:
            continue
        matches.append(fronts[0])
    return matches[0] if len(matches) == 1 else None


def insert_library_asset(space, asset_id, x, y, rotation=0):
    from app.api.v1.endpoints.cad_library import download_layout
    name = 'LIBRARY_' + re.sub(r'[^A-Za-z0-9_-]', '_', asset_id)
    doc = space.doc
    if name not in doc.blocks:
        if str(asset_id).startswith('tb:'):
            from app.services.cad.catalogtb_assets import resolve
            source = ezdxf.readfile(resolve(asset_id)['path'])
        else:
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
    if str(asset_id).startswith('tb:'):
        from app.services.cad.catalogtb_assets import resolve
        from app.services.cad.device_envelope import placement_bounds
        left,bottom,right,top = placement_bounds(resolve(asset_id))
        angle = math.radians(rotation)
        corners = [(px*math.cos(angle)-py*math.sin(angle),px*math.sin(angle)+py*math.cos(angle)) for px,py in ((left,bottom),(left,top),(right,bottom),(right,top))]
        ref.translate(x-min(p[0] for p in corners),y-min(p[1] for p in corners),0)
        return max(p[0] for p in corners)-min(p[0] for p in corners),max(p[1] for p in corners)-min(p[1] for p in corners)
    placed = bbox.extents([ref])
    if placed.has_data:
        ref.translate(x - placed.extmin.x, y - placed.extmin.y, 0)
    return bounds.size.x, bounds.size.y


def requested_asset(device, side=False):
    cad = device.get('cad') or (device.get('parameters') or {}).get('cad') or {}
    if str(cad.get('asset_id') or '').startswith('tb:'):
        from app.services.cad.catalogtb_assets import resolve
        item = resolve(cad['asset_id'], 'side' if side else 'front')
        return True, item['id']
    from app.api.v1.endpoints.cad_library import manifest
    from app.services.cad.device_families import build_families
    families = build_families(manifest()['items'])
    requested = cad.get('asset_id') or _exact_catalog_asset(device, families)
    if not requested:
        return False, None
    family = next((f for f in families if requested in f['asset_ids']), None)
    if family is None:
        raise ValueError('CAD chưa được nhận dạng là một thiết bị để bố trí tủ')
    face = 'side' if side else 'front'
    match = next((v['asset_id'] for v in family['views'] if v['face'] == face), None)
    if not match and not side:
        raise ValueError('CAD chưa xác nhận mặt trước; không tự dùng hình nguồn hoặc mặt cắt thay thế')
    return True, match

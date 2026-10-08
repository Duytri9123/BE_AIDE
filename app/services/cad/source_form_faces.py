"""Insert identified cabinet elevations for review without declaring fabrication approval."""
import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from app.services.cad import cabinet_templates


def insert_faces(space, dimensions, interior_offset):
    height, width, depth = map(float, dimensions)
    items = cabinet_templates.candidates(dict(height=height, width=width, depth=depth), kind='indoor')
    for item in items:
        nominal = item.get('dimensions') or {}
        if any(abs(nominal.get(axis, 0) - value) > .01 for axis, value in [('height', height), ('width', width)]):
            continue
        faces = {f['kind']: f for f in item.get('faces', []) if f.get('clean_bounds')}
        if not all(kind in faces for kind in ('inner_door', 'mounting_plate')):
            continue
        source = ezdxf.readfile(cabinet_templates.source_path(item))
        if source.units != 4:
            continue
        selected = []
        for kind, x in [('inner_door', 0), ('mounting_plate', interior_offset)]:
            left, bottom, right, top = faces[kind]['clean_bounds']
            if abs(right-left-width) > 1 or abs(top-bottom-height) > 1:
                break
            entities = []
            for entity in source.modelspace():
                if entity.dxftype() in ('TEXT', 'MTEXT', 'DIMENSION', 'POINT'):
                    continue
                ext = bbox.extents([entity])
                if ext.has_data and ext.extmin.x >= left-1 and ext.extmax.x <= right+1 and ext.extmin.y >= bottom-1 and ext.extmax.y <= top+1:
                    entities.append(entity)
            if not entities:
                break
            selected.append((kind, x, left, bottom, entities))
        if len(selected) != 2:
            continue
        for kind, x, left, bottom, entities in selected:
            name = 'CABINET_SOURCE_' + item['id'].replace('-', '_') + '_' + kind
            block = space.doc.blocks.new(name)
            importer = Importer(source, space.doc)
            importer.import_entities(entities, target_layout=block)
            importer.finalize()
            space.add_blockref(name, (x-left, -bottom))
        return dict(template_id=item['id'], source=item['filename'], source_dimensions=nominal,
                    requested_dimensions=dict(height=height, width=width, depth=depth),
                    faces=['inner_door', 'mounting_plate'], scale=1,
                    status='source_front_faces_review', depth_adjusted=False,
                    depth_change_required=abs(nominal.get('depth', 0)-depth) > .01)
    return None

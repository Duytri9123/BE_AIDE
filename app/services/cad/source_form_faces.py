"""Reuse the complete cabinet source sheet, keeping all source views and hardware."""
import ezdxf
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
        door = faces['inner_door']['clean_bounds']
        equipment = faces['mounting_plate']['clean_bounds']
        if any(abs(b[2]-b[0]-width)>1 or abs(b[3]-b[1]-height)>1 for b in (door,equipment)):
            continue
        if abs(equipment[1]-door[1])>1:
            continue
        source = ezdxf.readfile(cabinet_templates.source_path(item))
        if source.units != 4 or not len(source.modelspace()):
            continue
        name = 'CABINET_SOURCE_' + item['id'].replace('-', '_') + '_complete'
        block = space.doc.blocks.new(name)
        importer = Importer(source, space.doc)
        importer.import_entities(source.modelspace(), target_layout=block)
        importer.finalize()
        space.add_blockref(name, (-door[0], -door[1]))
        return dict(template_id=item['id'], source=item['filename'], source_dimensions=nominal,
                    requested_dimensions=dict(height=height, width=width, depth=depth),
                    faces=[f['kind'] for f in item.get('faces', [])], scale=1,
                    complete_source_sheet=True, source_entity_count=len(source.modelspace()),
                    interior_offset=equipment[0]-door[0],
                    face_mapping={f['kind']:dict(source_label=f.get('source_label'),bounds=[f['clean_bounds'][0]-door[0],f['clean_bounds'][1]-door[1],f['clean_bounds'][2]-door[0],f['clean_bounds'][3]-door[1]]) for f in item.get('faces',[]) if f.get('clean_bounds')},
                    side_view_review=dict(status='source_only_depth_not_verified',purpose=['enclosure_depth','mounting_plate_offset','device_projection','busbar_depth_layers','cable_bend_space'],missing=['device_side_geometry','mounting_offsets','cable_bend_radius','busbar_depth_layers']),
                    status='complete_source_form_review', depth_adjusted=False,
                    depth_change_required=abs(nominal.get('depth', 0)-depth) > .01)
    return None

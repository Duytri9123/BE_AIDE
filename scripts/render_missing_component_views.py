"""Render the remaining isolated DXF views; leave all DXF geometry untouched."""
import json
from pathlib import Path

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
inventory = json.loads((base/'full_accessory_cad_inventory.json').read_text(encoding='utf8'))
for row in inventory['records']:
    if row['kind'] != 'view' or row.get('preview'):
        continue
    source = base/row['cad_dxf']
    target = source.with_suffix('.svg')
    doc = ezdxf.readfile(source)
    backend = svg.SVGBackend()
    Frontend(RenderContext(doc), backend).draw_layout(doc.modelspace(), finalize=True)
    try:
        markup = backend.get_string(layout.Page(180,180,layout.Units.mm,
                                                 margins=layout.Margins.all(5)))
    except ValueError as exc:
        if 'empty bounding box' not in str(exc):
            raise
        # Some isolated views reference a nested anonymous block that ezdxf's
        # renderer skips. Explode an in-memory copy for the preview only.
        for insert in list(doc.modelspace().query('INSERT')):
            insert.explode()
        backend = svg.SVGBackend()
        Frontend(RenderContext(doc), backend).draw_layout(doc.modelspace(), finalize=True)
        try:
            markup = backend.get_string(layout.Page(180,180,layout.Units.mm,
                                                     margins=layout.Margins.all(5)))
        except ValueError as second:
            if 'empty bounding box' not in str(second):
                raise
            print(row['id'], 'no visible geometry')
            continue
    target.write_text(markup,encoding='utf8')
    row['preview'] = target.relative_to(base).as_posix()
    print(row['id'], len(markup), row['preview'])
(base/'full_accessory_cad_inventory.json').write_text(
    json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

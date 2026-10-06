"""Read each isolated DXF before labeling device views.

Face names are accepted only when a view's CAD label says so. Bounding boxes
and block transforms are recorded as evidence, never used alone to claim a face.
"""
import hashlib
import json
import re
from pathlib import Path

import ezdxf
from ezdxf import bbox

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
inventory = json.loads((base/'full_accessory_cad_inventory.json').read_text(encoding='utf8'))
views = [r for r in inventory['records'] if r['kind']=='view']
target = base/'THIET_BI_KHAC_2026/cad_view_analysis.json'
prior = json.loads(target.read_text(encoding='utf8'))['views'] if target.exists() else {}

FACE_RULES = (
    (r'(?<!\w)(?:FRONT|FONT|MẶT\s*TRƯỚC|MẶT\s*ĐỨNG)(?!\w)', 'Mặt trước'),
    (r'(?<!\w)(?:SIDE|CẠNH|MẶT\s*BÊN|MẶT\s*CẠNH|MẶT\s*HÔNG)(?!\w)', 'Mặt bên'),
    (r'(?<!\w)(?:TOP|ĐỈNH|MẶT\s*TRÊN|MẶT\s*BẰNG)(?!\w)', 'Mặt trên'),
    (r'(?<!\w)(?:BACK|REAR|MẶT\s*SAU)(?!\w)', 'Mặt sau'),
    (r'(?<!\w)(?:BOTTOM|MẶT\s*DƯỚI)(?!\w)', 'Mặt dưới'),
)

def explicit_face(name):
    faces = [face for pattern, face in FACE_RULES if re.search(pattern, name, re.I)]
    return faces[0] if len(faces)==1 else None

analysis = {}
errors = []
for row in views:
    source = base/row['cad_dxf']
    face = explicit_face(row['name'])
    if row['id'] in prior:
        cached = dict(prior[row['id']])
        cached['face'] = face
        cached['face_evidence'] = 'Tên góc nhìn trong CAD' if face else None
        analysis[row['id']] = cached
        continue
    try:
        doc = ezdxf.readfile(source)
        entities = list(doc.modelspace())
        box = bbox.extents(entities, fast=True)
        dimensions = ([round(box.size.x, 3),round(box.size.y, 3)]
                      if box.has_data and box.size.x>0 and box.size.y>0 else None)
        inserts = [{'name':e.dxf.name,
                    'rotation':round(e.dxf.get('rotation',0),3),
                    'xscale':round(e.dxf.get('xscale',1),4),
                    'yscale':round(e.dxf.get('yscale',1),4)}
                   for e in entities if e.dxftype()=='INSERT']
        preview = base/row['preview'] if row.get('preview') else None
        digest = hashlib.sha256(preview.read_bytes()).hexdigest() if preview and preview.exists() else None
        analysis[row['id']] = {
            'face':face, 'face_evidence':'Tên góc nhìn trong CAD' if face else None,
            'drawing_name':row['name'], 'bounds_drawing_units':dimensions,
            'inserts':inserts, 'entity_types':sorted({e.dxftype() for e in entities}),
            'preview_sha256':digest,
        }
    except Exception as exc:
        errors.append({'id':row['id'],'error':str(exc)})
        analysis[row['id']] = {'face':explicit_face(row['name']),
            'face_evidence':'Tên góc nhìn trong CAD' if explicit_face(row['name']) else None,
            'drawing_name':row['name'],'bounds_drawing_units':None,
            'inserts':[],'entity_types':[],'preview_sha256':None}

target.write_text(json.dumps({'source_dwg_sha256':inventory['source_dwg_sha256'],
                              'views':analysis,'errors':errors},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'analyzed':len(analysis),
                  'faces_labeled':sum(bool(v['face']) for v in analysis.values()),
                  'errors':len(errors)},ensure_ascii=False))

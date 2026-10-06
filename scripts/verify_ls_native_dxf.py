"""Verify exported DXF pole states in AutoCAD and one device INSERT per file."""
import json
import re
import time
from pathlib import Path
import win32com.client

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
rows=json.loads((BASE/'price_with_cad.json').read_text(encoding='utf8'))
variants=json.loads((BASE/'native/variants.json').read_text(encoding='utf8'))
ids=sorted({r['cad_variant_id'] for r in rows if r['cad_variant_id']} | {v['id'] for v in variants})
app=win32com.client.GetActiveObject('AutoCAD.Application')
errors=[]
for i,variant_id in enumerate(ids,1):
    for old in list(app.Documents): old.Close(False)
    time.sleep(.7)
    for attempt in range(8):
        try:
            app.Documents.Open(str(BASE/'native'/(variant_id+'.dxf')))
            break
        except Exception:
            if attempt==7: raise
            time.sleep(1)
    time.sleep(.5)
    doc=app.ActiveDocument
    blocks=[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference']
    if len(blocks)!=1:
        errors.append((variant_id,'modelspace block count',len(blocks)))
        continue
    block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
    attrs={a.TagString.upper():a.TextString for a in block.GetAttributes()} if block.HasAttributes else {}
    target=re.search(r'-([234])P$',variant_id)
    if target:
        got=re.match(r'([234])P',attrs.get('POLES',''),re.I)
        if not got or got[1]!=target[1]: errors.append((variant_id,'POLES attribute',attrs.get('POLES')))
        props={p.PropertyName:str(p.Value) for p in block.GetDynamicBlockProperties()} if block.IsDynamicBlock else {}
        if 'Options' in props and not props['Options'].startswith(target[1]+'P:'):
            errors.append((variant_id,'Options visibility',props['Options']))
    print(f'{i}/{len(ids)} {variant_id}',flush=True)
for old in list(app.Documents): old.Close(False)
print(json.dumps({'checked':len(ids),'errors':errors},ensure_ascii=False))
if errors: raise SystemExit(1)

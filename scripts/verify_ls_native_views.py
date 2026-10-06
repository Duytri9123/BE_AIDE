"""Reopen every view DXF in AutoCAD and check its saved dynamic state."""
import json
import time
from pathlib import Path
import win32com.client

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
views=json.loads((BASE/'native/views.json').read_text(encoding='utf8'))
app=win32com.client.GetActiveObject('AutoCAD.Application')
errors=[]

def retry(call):
    for attempt in range(12):
        try: return call()
        except Exception:
            if attempt==11: raise
            time.sleep(.7)

for n,view in enumerate(views,1):
    for old in retry(lambda:list(app.Documents)):
        retry(lambda:old.Close(False))
    time.sleep(.35)
    retry(lambda:app.Documents.Open(str(BASE/view['dxf'])))
    time.sleep(.65)
    doc=retry(lambda:app.ActiveDocument)
    blocks=retry(lambda:[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference'])
    if len(blocks)!=1:
        errors.append((view['id'],'block_count',len(blocks)))
        continue
    block=retry(lambda:win32com.client.CastTo(blocks[0],'IAcadBlockReference'))
    props=retry(lambda:{p.PropertyName:str(p.Value) for p in block.GetDynamicBlockProperties()} if block.IsDynamicBlock else {})
    if props.get('Options')!=view['option']:
        errors.append((view['id'],'Options',props.get('Options'),view['option']))
    attrs=retry(lambda:{a.TagString.upper():a.TextString for a in block.GetAttributes()} if block.HasAttributes else {})
    for tag,expected in view['attributes'].items():
        if attrs.get(tag)!=expected:
            errors.append((view['id'],tag,attrs.get(tag),expected))
    if n%10==0 or n==len(views): print(f'{n}/{len(views)} checked',flush=True)
for old in retry(lambda:list(app.Documents)):
    retry(lambda:old.Close(False))
print(json.dumps({'checked':len(views),'errors':errors},ensure_ascii=False))
if errors: raise SystemExit(1)

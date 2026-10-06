"""Export Mitsubishi's existing dynamic view states from native CAD copies."""
import json
import re
import time
from pathlib import Path
import ezdxf
import pythoncom
import win32com.client

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI'
NATIVE=BASE/'native'
source=json.loads((NATIVE/'manifest.json').read_text(encoding='utf8'))
index_path=NATIVE/'views.json'
views=json.loads(index_path.read_text(encoding='utf8')) if index_path.exists() else []
completed={v['id'] for v in views}
try: app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app=win32com.client.Dispatch('AutoCAD.Application')
    app.Visible=True
    time.sleep(4)

def retry(call):
    for attempt in range(12):
        try: return call()
        except Exception:
            if attempt==11: raise
            time.sleep(.8)

def close_all():
    for doc in retry(lambda:list(app.Documents)):
        retry(lambda:doc.Close(False))

def slug(s):
    return re.sub(r'-+','-',re.sub(r'[^A-Z0-9]+','-',s.upper())).strip('-')

# Export the states belonging to each placed device. The dynamic definition
# offers other models too, but their views must not be presented as this model.
def relevant(item, option):
    source_id=item['id']
    if source_id.startswith('MIT-D04-C2-'):
        own=item['dynamic_properties'][0]['value'].split(':')[0]
        return option==own+': Side View'
    if source_id.startswith('MIT-D04-C3-'):
        own=item['dynamic_properties'][0]['value'].split(':')[0]
        return option in ('Side View',own+': Cover')
    return True

jobs=[]
for item in source:
    prop=next((p for p in item['dynamic_properties'] if p['name'] in ('Options','Visibility1')),None)
    if not prop: continue
    for option in prop['allowed']:
        if option==prop['value'] or not relevant(item,option): continue
        view_id=item['id']+'-VIEW-'+slug(option)
        if view_id not in completed: jobs.append((item,prop['name'],option,view_id))

vec=lambda v:win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
for n,(item,property_name,option,view_id) in enumerate(jobs,1):
    close_all()
    retry(lambda:app.Documents.Open(str(NATIVE/(item['id']+'.dwg'))))
    time.sleep(.6)
    doc=retry(lambda:app.ActiveDocument)
    blocks=retry(lambda:[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference'])
    if len(blocks)!=1: raise RuntimeError((item['id'],len(blocks)))
    block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
    selected=next(p for p in block.GetDynamicBlockProperties() if p.PropertyName==property_name)
    selected.Value=option
    retry(lambda:doc.Regen(1))
    time.sleep(.4)
    dwg=NATIVE/(view_id+'.dwg')
    dxf=NATIVE/(view_id+'.dxf')
    if dwg.exists(): dwg.unlink()
    if dxf.exists(): dxf.unlink()
    doc.SaveAs(str(dwg))
    time.sleep(.35)
    lo,hi=block.GetBoundingBox()
    margin=max(hi[0]-lo[0],hi[1]-lo[1])*.05
    app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)),vec((hi[0]+margin,hi[1]+margin,0)))
    retry(lambda:doc.Regen(1))
    time.sleep(.35)
    selection=doc.SelectionSets.Add('CODEX_MIT_VIEWS')
    try:
        selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
        doc.Export(str(NATIVE/view_id),'WMF',selection)
    finally:
        selection.Delete()
    doc.SaveAs(str(dxf),65)
    time.sleep(.35)
    insert=next(iter(ezdxf.readfile(dxf).modelspace()))
    attrs={a.dxf.tag.upper():a.dxf.text for a in insert.attribs}
    views.append({'id':view_id,'source_id':item['id'],'property':property_name,
                  'option':option,'attributes':attrs,'dwg':'native/'+dwg.name,
                  'dxf':'native/'+dxf.name,'wmf':'native/'+view_id+'.wmf',
                  'method':'AutoCAD existing dynamic visibility state; no geometry added'})
    index_path.write_text(json.dumps(views,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'{n}/{len(jobs)} {view_id}',flush=True)
close_all()

"""Export each original AutoCAD dynamic Options state as DWG, DXF and WMF.

Only existing dynamic visibility states and their paired attribute values are used.
The source DWG and the 33 extracted source blocks are never edited.
"""
import json
import re
import time
from pathlib import Path
import pythoncom
import win32com.client
import ezdxf

BASE=Path(__file__).resolve().parents[2]/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
NATIVE=BASE/'native'
source=json.loads((NATIVE/'manifest.json').read_text(encoding='utf8'))
variants=json.loads((NATIVE/'variants.json').read_text(encoding='utf8'))
known_variants={v['id'] for v in variants}
index_path=NATIVE/'views.json'
views=json.loads(index_path.read_text(encoding='utf8')) if index_path.exists() else []
completed={v['id'] for v in views}
try:
    app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app=win32com.client.Dispatch('AutoCAD.Application')
    app.Visible=True
    time.sleep(4)

def slug(s):
    return re.sub(r'-+','-',re.sub(r'[^A-Z0-9]+','-',s.upper())).strip('-')

def paired_poles(option,allowed):
    u=option.upper()
    if u=='COVER':
        return next((v for v in allowed if v.lower().endswith('/c')),None)
    m=re.match(r'([1-4]P(?:\+N)?)\s*:\s*(FRONT|COVER)',u)
    if m:
        value=m[1].lower() + ('/f' if m[2]=='FRONT' else '/c')
        return next((v for v in allowed if v.lower()==value),None)
    m=re.match(r'(?:SPACE|COVER SPACE)\s*([2-4]P|2/3P)?',u)
    if m:
        wanted={'2/3P':'2/3P/s','4P':'4P/s',None:'1P/space'}[m[1]]
        return next((v for v in allowed if v.lower()==wanted.lower()),None)
    return next((v for v in allowed if v.lower()=='none'),None)

def set_property(block,name,value):
    for prop in block.GetDynamicBlockProperties():
        if prop.PropertyName==name:
            prop.Value=value
            return

def wait_open(path):
    for attempt in range(10):
        try:
            app.Documents.Open(str(path))
            time.sleep(.65)
            return app.ActiveDocument
        except Exception:
            if attempt==9: raise
            time.sleep(1)

def close_all():
    docs=None
    for attempt in range(20):
        try:
            docs=list(app.Documents)
            break
        except Exception:
            if attempt==19: raise
            time.sleep(1)
    for doc in docs:
        for attempt in range(8):
            try:
                doc.Close(False)
                break
            except Exception:
                if attempt==7: raise
                time.sleep(.7)

jobs=[]
for item in source:
    options=next((p for p in item['dynamic_properties'] if p['name']=='Options'),None)
    if not options: continue
    for option in options['allowed']:
        if option==options['value']: continue
        m=re.match(r'([234])P:\s*FRONT',option,re.I)
        if m and item['id']+f'-{m[1]}P' in known_variants:
            continue
        view_id=item['id']+'-VIEW-'+slug(option)
        if view_id not in completed: jobs.append((item,option,view_id))

for n,(item,option,view_id) in enumerate(jobs,1):
    chosen=None
    close_all()
    doc=wait_open(NATIVE/(item['id']+'.dwg'))
    blocks=[e for e in doc.ModelSpace if e.ObjectName=='AcDbBlockReference']
    if len(blocks)!=1: raise RuntimeError(f'{item["id"]}: {len(blocks)} blocks')
    block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
    set_property(block,'Options',option)
    states={p.PropertyName:p for p in block.GetDynamicBlockProperties()}
    pole_value=paired_poles(option,list(states['Poles'].AllowedValues)) if 'Poles' in states else None
    if pole_value: set_property(block,'Poles',pole_value)
    # Contactors expose their type and current as genuine dynamic properties.
    rated=re.match(r'(\d+)A:\s*FRONT',option,re.I)
    if rated and 'Rate' in states:
        rate=str(int(rated[1]))+'A'
        if rate in list(states['Rate'].AllowedValues): set_property(block,'Rate',rate)
    if rated and 'Type' in states:
        types=list(states['Type'].AllowedValues)
        number=str(int(rated[1]))
        chosen=next((v for v in types if re.fullmatch(r'MC-'+number+r'[a-z]?',str(v),re.I)),None)
        if chosen: set_property(block,'Type',chosen)
    attributes={}
    if block.HasAttributes:
        for attr in block.GetAttributes():
            tag=attr.TagString.upper()
            if tag=='POLES' and pole_value: attr.TextString=pole_value
            elif tag=='RATE' and rated: attr.TextString=str(int(rated[1]))+'A'
            elif tag=='TYPE' and rated and chosen: attr.TextString=chosen
            attributes[tag]=attr.TextString
    doc.Regen(1)
    time.sleep(.4)
    dwg=NATIVE/(view_id+'.dwg')
    dxf=NATIVE/(view_id+'.dxf')
    if dwg.exists(): dwg.unlink()
    if dxf.exists(): dxf.unlink()
    doc.SaveAs(str(dwg))
    time.sleep(.4)
    lo,hi=block.GetBoundingBox()
    margin=max(hi[0]-lo[0],hi[1]-lo[1])*.05
    vector=lambda v: win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
    app.ZoomWindow(vector((lo[0]-margin,lo[1]-margin,0)),vector((hi[0]+margin,hi[1]+margin,0)))
    doc.Regen(1)
    time.sleep(.4)
    selection=doc.SelectionSets.Add('CODEX_LS_VIEWS')
    try:
        selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
        doc.Export(str(NATIVE/view_id),'WMF',selection)
    finally:
        selection.Delete()
    doc.SaveAs(str(dxf),65)
    time.sleep(.4)
    saved_insert=next(iter(ezdxf.readfile(dxf).modelspace()))
    attributes={a.dxf.tag.upper():a.dxf.text for a in saved_insert.attribs}
    views.append({'id':view_id,'source_id':item['id'],'option':option,'poles_property':pole_value,
                  'attributes':attributes,'dwg':'native/'+dwg.name,'dxf':'native/'+dxf.name,
                  'wmf':'native/'+view_id+'.wmf',
                  'method':'AutoCAD existing dynamic Options state; source geometry unchanged'})
    index_path.write_text(json.dumps(views,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'{n}/{len(jobs)} {view_id}',flush=True)
close_all()

"""Export existing dynamic CAD views for price-matched device families."""
import json
import re
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
FOLDERS={
    'schneider':'SCHNEIDER_D01_DU_LIEU_MOI',
    'abb':'ABB_D03_DU_LIEU_MOI',
}
brand=sys.argv[1].lower()
base=CAT/FOLDERS[brand]
native=base/'native'
manifest=json.loads((native/'manifest.json').read_text(encoding='utf8'))
views_path=native/'views.json'
views=json.loads(views_path.read_text(encoding='utf8')) if views_path.exists() else []
done={v['id'] for v in views}
selected={
    'schneider':{'SCH-D01-C3-I02','SCH-D01-C3-I03','SCH-D01-C5-I02'},
    'abb':{'ABB-D03-C3-I01','ABB-D03-C3-I03','ABB-D03-C3-I06','ABB-D03-C4-I01','ABB-D03-C4-I02','ABB-D03-C4-I03',
           'ABB-D03-C6-I01','ABB-D03-C6-I02','ABB-D03-C6-I03'},
}[brand]

def wanted(item, option):
    if item['id']=='ABB-D03-C3-I06':
        return option in {'4P: Front View','Side View','2P: Cover','4P: Cover'}
    if item['id'].startswith('ABB-D03-C4-'):
        return option in {'4P: Front View','Side View','3P: Cover','4P: Cover'}
    if item['id'].startswith('ABB-D03-C6-'):
        return option in {'4P: Front View','Side View','3P: Cover','4P: Cover',
                          '3P: Cover (small)','3P: Cover (big)',
                          '4P: Cover (small)','4P: Cover (big)'}
    return bool(re.fullmatch(r'[1-4]P: (?:Front View|Cover)|Side View',option))

def slug(value):
    return re.sub(r'-+','-',re.sub(r'[^A-Z0-9]+','-',value.upper())).strip('-')

jobs=[]
for item in manifest:
    if item['id'] not in selected: continue
    prop=next((x for x in item['dynamic_properties'] if x['name']=='Options'),None)
    if not prop: continue
    for option in prop['allowed']:
        if option==prop['value'] or not wanted(item,option): continue
        vid=item['id']+'-VIEW-'+slug(option)
        if vid not in done: jobs.append((item,option,vid))

app=win32com.client.GetActiveObject('AutoCAD.Application')
def retry(fn):
    for attempt in range(20):
        try: return fn()
        except (pythoncom.com_error,TypeError):
            if attempt==19: raise
            time.sleep(1)

def set_prop(block,name,value):
    for prop in retry(lambda:block.GetDynamicBlockProperties()):
        if prop.PropertyName==name:
            retry(lambda: setattr(prop,'Value',value))
            return

for old in retry(lambda:list(app.Documents)):
    retry(lambda old=old:old.Close(False))
for i,(item,option,vid) in enumerate(jobs,1):
    retry(lambda:app.Documents.Open(str((native/(item['id']+'.dwg')).resolve())))
    doc=retry(lambda:app.ActiveDocument)
    block=win32com.client.CastTo(next(e for e in retry(lambda:list(doc.ModelSpace)) if e.ObjectName=='AcDbBlockReference'),
                                 'IAcadBlockReference')
    set_prop(block,'Options',option)
    match=re.match(r'([1-4])P: (Front View|Cover)(?: \((small|big)\))?',option)
    pole_value=None
    if match:
        suffix='f' if match[2]=='Front View' else ('cs' if match[3]=='small' else 'cb' if match[3]=='big' else 'c')
        pole_value=match[1]+'P/'+suffix
        set_prop(block,'Poles',pole_value)
    device_type=None
    if item['id']=='ABB-D03-C3-I06' and match and match[1]=='4':
        device_type='FH204'
        set_prop(block,'Type',device_type)
    attrs={}
    if retry(lambda:block.HasAttributes):
        for attr in retry(lambda:block.GetAttributes()):
            tag=retry(lambda:attr.TagString).upper()
            if tag=='POLES' and pole_value: retry(lambda:setattr(attr,'TextString',pole_value))
            if tag=='TYPE' and device_type: retry(lambda:setattr(attr,'TextString',device_type))
            attrs[tag]=retry(lambda:attr.TextString)
    retry(lambda:doc.Regen(1))
    time.sleep(.25)
    dwg=native/(vid+'.dwg')
    dxf=native/(vid+'.dxf')
    if dwg.exists(): dwg.unlink()
    if dxf.exists(): dxf.unlink()
    retry(lambda:doc.SaveAs(str(dwg.resolve())))
    retry(lambda:doc.SaveAs(str(dxf.resolve()),65))
    views.append({'id':vid,'source_id':item['id'],'option':option,
                  'poles_property':pole_value,'attributes':attrs,
                  'dwg':'native/'+dwg.name,'dxf':'native/'+dxf.name,
                  'method':'Existing AutoCAD dynamic state, WBlock geometry unchanged'})
    views_path.write_text(json.dumps(views,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    retry(lambda:doc.Close(False))
    print(i,'/',len(jobs),vid,flush=True)

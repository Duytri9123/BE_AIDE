"""WBlock the placed device references from the original DWG, without redraw."""
import json
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
BRANDS={
    'schneider':('D01','SCHNEIDER_D01_DU_LIEU_MOI','SCH'),
    'abb':('D03','ABB_D03_DU_LIEU_MOI','ABB'),
    'shihlin':('D06','SHIHLIN_D06_DU_LIEU_MOI','SHI'),
    'osung':('D05','OSUNG_D05_DU_LIEU_MOI','OSU'),
}
zone,folder,prefix=BRANDS[sys.argv[1].lower()]
base=CAT/folder
native=base/'native'
native.mkdir(exist_ok=True)
source=ROOT/'Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
items=[]
for path in sorted((CAT/'04_BO_THIET_BI_DXF'/zone).glob('*/thong_tin.json')):
    group=json.loads(path.read_text(encoding='utf8'))
    cluster=int(group['id'].split('cluster')[1])
    for i,view in enumerate(group['views'],1):
        handles=view.get('source_handles') or []
        if handles:
            items.append({'id':f'{prefix}-{zone}-C{cluster}-I{i:02d}',
                          'group':group['name'],'view_name':view['name'],
                          'source_handles':handles})

try: app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app=win32com.client.Dispatch('AutoCAD.Application')
    app.Visible=True
    time.sleep(4)

def retry(fn):
    for attempt in range(20):
        try: return fn()
        except pythoncom.com_error:
            if attempt==19: raise
            time.sleep(1.5)

docs=retry(lambda:list(app.Documents))
doc=next((d for d in docs if Path(d.FullName).resolve()==source.resolve()),None)
if doc is None:
    for old in docs: retry(lambda:old.Close(False))
    retry(lambda:app.Documents.Open(str(source)))
    time.sleep(3)
    doc=retry(lambda:app.ActiveDocument)
manifest_path=native/'manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8')) if manifest_path.exists() else []
done={x['id'] for x in manifest}
vec=lambda v:win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
for n,item in enumerate(items,1):
    if item['id'] in done: continue
    entities=[retry(lambda h=h:doc.HandleToObject(h)) for h in item['source_handles']]
    blocks=[e for e in entities if e.ObjectName=='AcDbBlockReference']
    if len(blocks)!=1:
        print('SKIP',item['id'],'block_count',len(blocks),flush=True)
        continue
    block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
    props=[]
    if block.IsDynamicBlock:
        for prop in retry(lambda:block.GetDynamicBlockProperties()):
            props.append({'name':prop.PropertyName,'value':str(prop.Value),
                          'allowed':[str(v) for v in (prop.AllowedValues or [])]})
    attrs=[{'tag':a.TagString,'text':a.TextString} for a in block.GetAttributes()] if block.HasAttributes else []
    lo,hi=retry(lambda:block.GetBoundingBox())
    margin=max(hi[0]-lo[0],hi[1]-lo[1])*.04
    retry(lambda:app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)),
                                vec((hi[0]+margin,hi[1]+margin,0))))
    retry(lambda:doc.Regen(1))
    time.sleep(.3)
    selection=retry(lambda:doc.SelectionSets.Add('CODEX_BRAND_NATIVE'))
    stem=native/item['id']
    try:
        selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
        if stem.with_suffix('.dwg').exists(): stem.with_suffix('.dwg').unlink()
        retry(lambda:doc.Wblock(str(stem.with_suffix('.dwg')),selection))
        retry(lambda:doc.Export(str(stem),'WMF',selection))
    finally:
        retry(lambda:selection.Delete())
    im=Image.open(stem.with_suffix('.wmf')).convert('RGB')
    dark=im.point(lambda x:255 if x<245 else 0)
    box=dark.getbbox()
    if box:
        pad=round(max(box[2]-box[0],box[3]-box[1])*.035)
        im=im.crop((max(0,box[0]-pad),max(0,box[1]-pad),
                    min(im.width,box[2]+pad),min(im.height,box[3]+pad)))
    im.save(native/(stem.name+'-crop.png'))
    manifest.append({**item,'source_handle':retry(lambda:block.Handle),'block_name':retry(lambda:block.Name),
                     'omitted_external_handles':[retry(lambda e=e:e.Handle) for e in entities if e.ObjectName!='AcDbBlockReference'],
                     'dynamic_properties':props,'attributes':attrs,'bbox':[lo,hi],
                     'dwg':'native/'+stem.name+'.dwg',
                     'preview':'native/'+stem.name+'-crop.png',
                     'method':'AutoCAD WBlock and WMF from original block; no geometry altered'})
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(n,'/',len(items),item['id'],attrs,flush=True)
retry(lambda:doc.Close(False))

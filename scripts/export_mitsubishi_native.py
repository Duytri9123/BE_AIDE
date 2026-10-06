"""Export the 17 Mitsubishi D04 device blocks directly from the source DWG."""
import json
import time
from pathlib import Path
import pythoncom
import win32com.client

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
BASE=CAT/'MITSUBISHI_D04_DU_LIEU_MOI'
NATIVE=BASE/'native'
NATIVE.mkdir(parents=True,exist_ok=True)
source_dwg=ROOT/'Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
source=[]
for path in sorted((CAT/'04_BO_THIET_BI_DXF/D04').glob('*/thong_tin.json')):
    cluster=int(path.parent.name.split('_')[1].removeprefix('cluster'))
    group=json.loads(path.read_text(encoding='utf8'))
    for i,view in enumerate(group['views'],1):
        if not view.get('source_handles'): continue
        source.append({'id':f'MIT-D04-C{cluster}-I{i:02d}','group':group['name'],
                       'source_handles':view['source_handles'],'prior_dxf':view['file']})
assert len(source)==17,len(source)
try: app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app=win32com.client.Dispatch('AutoCAD.Application')
    app.Visible=True
    time.sleep(4)
docs=list(app.Documents)
doc=next((d for d in docs if Path(d.FullName).resolve()==source_dwg.resolve()),None)
if doc is None:
    for d in docs: d.Close(False)
    for attempt in range(12):
        try:
            app.Documents.Open(str(source_dwg))
            break
        except Exception:
            if attempt==11: raise
            time.sleep(2)
    time.sleep(3)
    doc=app.ActiveDocument
assert Path(doc.FullName).resolve()==source_dwg.resolve()
vec=lambda v:win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
manifest_path=NATIVE/'manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf8')) if manifest_path.exists() else []
done={m['id'] for m in manifest}
for n,item in enumerate(source,1):
    if item['id'] in done: continue
    entities=[doc.HandleToObject(h) for h in item['source_handles']]
    blocks=[e for e in entities if e.ObjectName=='AcDbBlockReference']
    if len(blocks)!=1: raise RuntimeError((item['id'],len(blocks)))
    block=win32com.client.CastTo(blocks[0],'IAcadBlockReference')
    omitted=[e.Handle for e in entities if e.ObjectName!='AcDbBlockReference']
    entities=blocks  # External title and loose annotation are outside the device.
    props=[]
    if block.IsDynamicBlock:
        for prop in block.GetDynamicBlockProperties():
            props.append({'name':prop.PropertyName,'value':str(prop.Value),
                          'allowed':[str(v) for v in (prop.AllowedValues or [])]})
    attrs=[{'tag':a.TagString,'text':a.TextString} for a in block.GetAttributes()] if block.HasAttributes else []
    lo,hi=block.GetBoundingBox()
    margin=max(hi[0]-lo[0],hi[1]-lo[1])*.04
    app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)),vec((hi[0]+margin,hi[1]+margin,0)))
    doc.Regen(1)
    time.sleep(.5)
    selection=doc.SelectionSets.Add('CODEX_MITSUBISHI_NATIVE')
    try:
        selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,entities))
        stem=NATIVE/item['id']
        doc.Wblock(str(stem.with_suffix('.dwg')),selection)
        doc.Export(str(stem),'WMF',selection)
    finally:
        selection.Delete()
    manifest.append({**item,'source_handles':[block.Handle],'omitted_external_handles':omitted,
                     'block_name':block.Name,'dynamic_properties':props,
                     'attributes':attrs,'bbox_including_hidden_geometry':[lo,hi],
                     'dwg':'native/'+item['id']+'.dwg','wmf':'native/'+item['id']+'.wmf',
                     'method':'AutoCAD WBlock + WMF from original D04 selection, no geometry altered'})
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'{n}/{len(source)} {item["id"]}',flush=True)
doc.Close(False)

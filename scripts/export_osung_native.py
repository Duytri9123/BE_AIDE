"""Export the one O-Sung D05 device block, preserving source geometry."""
import json
import time
from pathlib import Path

import pythoncom
import win32com.client
from PIL import Image

root = Path(__file__).resolve().parents[2]
base = root / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/OSUNG_D05_DU_LIEU_MOI'
native = base / 'native'
native.mkdir(parents=True, exist_ok=True)
source = root / 'Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg'
handle = '37B0B8'  # D05_cluster6_O-Sung/thong_tin.json
try:
    app = win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app = win32com.client.Dispatch('AutoCAD.Application')
    app.Visible = True
    time.sleep(4)
doc = next((d for d in app.Documents if Path(d.FullName).resolve() == source.resolve()), None)
opened = doc is None
if opened:
    doc = app.Documents.Open(str(source))
for attempt in range(20):
    try:
        block = win32com.client.CastTo(doc.HandleToObject(handle), 'IAcadBlockReference')
        assert block.ObjectName == 'AcDbBlockReference'
        break
    except pythoncom.com_error:
        if attempt == 19:
            raise
        time.sleep(2)
stem = native / 'OSU-D05-C6-I01'
props = []
if block.IsDynamicBlock:
    for prop in block.GetDynamicBlockProperties():
        props.append({'name':prop.PropertyName, 'value':str(prop.Value),
                      'allowed':[str(x) for x in (prop.AllowedValues or [])]})
lo, hi = block.GetBoundingBox()
margin = max(hi[0]-lo[0],hi[1]-lo[1]) * .04
vec = lambda v:win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)),
               vec((hi[0]+margin,hi[1]+margin,0)))
doc.Regen(1)
selection = doc.SelectionSets.Add('CODEX_OSUNG_NATIVE')
try:
    selection.AddItems(win32com.client.VARIANT(
        pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
    doc.Wblock(str(stem.with_suffix('.dwg')),selection)
    doc.Export(str(stem),'WMF',selection)
finally:
    selection.Delete()
manifest = [{'id':stem.name,'source_handle':handle,'block_name':block.Name,
             'dynamic_properties':props,'bbox_including_hidden_geometry':[lo,hi],
             'dwg':'native/'+stem.name+'.dwg','wmf':'native/'+stem.name+'.wmf',
             'method':'AutoCAD WBlock + WMF from original D05 block; no geometry altered'}]
(native/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
im=Image.open(stem.with_suffix('.wmf')).convert('RGB')
dark=im.point(lambda x:255 if x<245 else 0)
box=dark.getbbox()
if box:
    pad=round(max(box[2]-box[0],box[3]-box[1])*.035)
    im=im.crop((max(0,box[0]-pad),max(0,box[1]-pad),
                min(im.width,box[2]+pad),min(im.height,box[3]+pad)))
im.save(native/(stem.name+'-crop.png'))
if opened:
    doc.Close(False)
print(json.dumps(manifest[0],ensure_ascii=False))

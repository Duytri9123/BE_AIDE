"""Export original selected LS blocks through AutoCAD, preserving dynamic visibility."""
import json
import time
from pathlib import Path
import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
BASE = CAT / 'LS_D02_DU_LIEU_MOI'
OUT = BASE / 'native'
OUT.mkdir(exist_ok=True)
app = win32com.client.GetActiveObject('AutoCAD.Application')
doc = app.ActiveDocument
assert Path(doc.FullName).resolve() == (ROOT / 'Tudien/THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg').resolve()
devices = json.loads((BASE / 'devices.json').read_text(encoding='utf8'))
views = {}
for path in (CAT / '04_BO_THIET_BI_DXF/D02').glob('*/thong_tin.json'):
    for view in json.loads(path.read_text(encoding='utf8'))['views']:
        views[view['file']] = view
vec = lambda v: win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, v)
old_center, old_height = doc.GetVariable('VIEWCTR'), doc.GetVariable('VIEWSIZE')
manifest = []
try:
    for index, item in enumerate(devices):
        view = views[item['cad_dxf']]
        handles = view['source_handles']
        entities = [doc.HandleToObject(h) for h in handles]
        block = entities[0]
        props = []
        if block.IsDynamicBlock:
            for prop in block.GetDynamicBlockProperties():
                props.append({'name': prop.PropertyName, 'value': str(prop.Value),
                              'allowed': [str(v) for v in (prop.AllowedValues or [])]})
        attrs = []
        if block.HasAttributes:
            attrs = [{'tag': a.TagString, 'text': a.TextString} for a in block.GetAttributes()]
        lo, hi = block.GetBoundingBox()
        margin = max(hi[0]-lo[0], hi[1]-lo[1])*.04
        app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)), vec((hi[0]+margin,hi[1]+margin,0)))
        doc.Regen(1)
        name = 'CODEX_LS_NATIVE_' + str(index)
        selection = doc.SelectionSets.Add(name)
        try:
            selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, entities))
            stem = OUT / item['id']
            if not stem.with_suffix('.dwg').exists():
                doc.WBlock(str(stem.with_suffix('.dwg')), selection)
            doc.Export(str(stem), 'WMF', selection)
        finally:
            selection.Delete()
        manifest.append({'id': item['id'], 'source_handles': handles, 'block_name': block.Name,
                         'dynamic_properties': props, 'attributes': attrs,
                         'bbox_including_hidden_geometry': [lo,hi],
                         'dwg': stem.with_suffix('.dwg').relative_to(CAT).as_posix(),
                         'wmf': stem.with_suffix('.wmf').relative_to(CAT).as_posix(),
                         'method': 'AutoCAD WBlock + WMF export of original selection; no geometry modified'})
        (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
        print(f"{index+1}/{len(devices)} {item['id']}", flush=True)
finally:
    app.ZoomCenter(vec((old_center[0], old_center[1], 0)), old_height)

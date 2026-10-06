"""Switch only existing dynamic 2P/4P visibility states in copied LS blocks."""
import json
import time
from pathlib import Path
import pythoncom
import win32com.client

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
OUT = BASE / 'native'
source = json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
app = win32com.client.GetActiveObject('AutoCAD.Application')
variants_path = OUT/'variants.json'
variants = json.loads(variants_path.read_text(encoding='utf8')) if variants_path.exists() else []
completed = {v['id'] for v in variants}
for item in source:
    options = next((p for p in item['dynamic_properties'] if p['name']=='Options'), None)
    if not options:
        continue
    for poles in (2,4):
        variant_id = item['id'] + f'-{poles}P'
        if variant_id in completed:
            continue
        choices = [s for s in options['allowed'] if s.lower().startswith(f'{poles}p: front')]
        if not choices:
            continue
        for open_doc in list(app.Documents):
            open_doc.Close(False)
        app.Documents.Open(str(OUT / (item['id']+'.dwg')))
        time.sleep(1.2)
        doc = app.ActiveDocument
        try:
            blocks = [e for e in doc.ModelSpace if e.ObjectName == 'AcDbBlockReference']
            if len(blocks) != 1:
                raise RuntimeError(f"{item['id']}: {len(blocks)} block references")
            block = blocks[0]
            for prop in block.GetDynamicBlockProperties():
                if prop.PropertyName == 'Options':
                    prop.Value = choices[0]
                elif prop.PropertyName == 'Poles':
                    prop.Value = f'{poles}P/f'
            if block.HasAttributes:
                for attr in block.GetAttributes():
                    if attr.TagString.upper() == 'POLES':
                        attr.TextString = f'{poles}P/f'
            doc.Regen(1)
            time.sleep(.7)
            state = {'Options': choices[0], 'Poles': f'{poles}P/f'}
            target = OUT / (variant_id+'.dwg')
            if target.exists():
                target.unlink()
            doc.SaveAs(str(target))
            time.sleep(.5)
            lo, hi = block.GetBoundingBox()
            margin = max(hi[0]-lo[0], hi[1]-lo[1])*.04
            vec = lambda v: win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
            app.ZoomWindow(vec((lo[0]-margin,lo[1]-margin,0)),vec((hi[0]+margin,hi[1]+margin,0)))
            doc.Regen(1)
            time.sleep(.8)
            doc = app.ActiveDocument
            selection = doc.SelectionSets.Add('CODEX_LS_VARIANT')
            try:
                selection.AddItems(win32com.client.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
                doc.Export(str(OUT/variant_id),'WMF',selection)
            finally:
                selection.Delete()
            variants.append({'id':variant_id,'source_id':item['id'],'poles':poles,
                             'option':choices[0], 'properties':state,
                             'dwg':str(target.relative_to(BASE)),
                             'wmf':str((OUT/(variant_id+'.wmf')).relative_to(BASE)),
                             'method':'existing AutoCAD dynamic visibility state in a copy of the original block'})
            variants_path.write_text(json.dumps(variants,ensure_ascii=False,indent=2),encoding='utf8')
            print(f"{len(variants)} {variant_id}",flush=True)
        finally:
            time.sleep(.5)
            for open_doc in list(app.Documents):
                open_doc.Close(False)

"""Save matched native LS blocks as AutoCAD 2018 DXF, retaining dynamic states."""
import json
import time
from pathlib import Path
import win32com.client

BASE = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
NATIVE = BASE/'native'
rows=json.loads((BASE/'price_with_cad.json').read_text(encoding='utf8'))
sources=json.loads((NATIVE/'manifest.json').read_text(encoding='utf8'))
variants=json.loads((NATIVE/'variants.json').read_text(encoding='utf8'))
ids=sorted({r['cad_variant_id'] for r in rows if r.get('cad_variant_id')} | {s['id'] for s in sources} | {v['id'] for v in variants})
app=win32com.client.GetActiveObject('AutoCAD.Application')
for index,variant_id in enumerate(ids,1):
    source=NATIVE/(variant_id+'.dwg')
    target=NATIVE/(variant_id+'.dxf')
    if target.exists() and target.stat().st_size>1000:
        continue
    for doc in list(app.Documents):
        doc.Close(False)
    app.Documents.Open(str(source))
    time.sleep(.8)
    doc=app.ActiveDocument
    doc.SaveAs(str(target),65)
    time.sleep(.5)
    print(f'{index}/{len(ids)} {variant_id}',flush=True)
for doc in list(app.Documents):
    doc.Close(False)

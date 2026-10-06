"""Save the 17 already isolated Mitsubishi source blocks as DXF via AutoCAD."""
import json
import time
from pathlib import Path
import win32com.client

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/MITSUBISHI_D04_DU_LIEU_MOI/native'
manifest = json.loads((base / 'manifest.json').read_text(encoding='utf8'))
app = win32com.client.GetActiveObject('AutoCAD.Application')

def retry(call):
    for i in range(15):
        try:
            return call()
        except Exception:
            if i == 14:
                raise
            time.sleep(.8)

for i, item in enumerate(manifest, 1):
    dxf = base / (item['id'] + '.dxf')
    if dxf.exists():
        continue
    for doc in retry(lambda: list(app.Documents)):
        retry(lambda: doc.Close(False))
    retry(lambda: app.Documents.Open(str(base / (item['id'] + '.dwg'))))
    doc = retry(lambda: app.ActiveDocument)
    retry(lambda: doc.SaveAs(str(dxf), 65))
    print(f'{i}/{len(manifest)} {dxf.name}', flush=True)
for doc in retry(lambda: list(app.Documents)):
    retry(lambda: doc.Close(False))

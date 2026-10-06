"""Save selected original WBlock copies as editable DXF through AutoCAD."""
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client

root=Path(__file__).resolve().parents[2]
catalog=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
paths=[catalog/arg for arg in sys.argv[1:]]
app=win32com.client.GetActiveObject('AutoCAD.Application')

def retry(fn):
    for attempt in range(20):
        try: return fn()
        except pythoncom.com_error:
            if attempt==19: raise
            time.sleep(1)

for path in paths:
    assert path.suffix.lower()=='.dwg' and path.is_file(),path
    dxf=path.with_suffix('.dxf')
    if dxf.exists(): continue
    retry(lambda:app.Documents.Open(str(path.resolve())))
    doc=retry(lambda:app.ActiveDocument)
    retry(lambda:doc.SaveAs(str(dxf.resolve()),65))
    retry(lambda:doc.Close(False))
    print(dxf.relative_to(catalog),flush=True)

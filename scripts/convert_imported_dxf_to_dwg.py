"""Save an inspected DXF as DWG in AutoCAD without changing its entities."""
import sys
import time
from pathlib import Path

import pythoncom
import win32com.client

source = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
assert source.is_file() and source.suffix.lower() == '.dxf'
assert target.suffix.lower() == '.dwg'

try:
    app = win32com.client.GetActiveObject('AutoCAD.Application')
except Exception:
    app = win32com.client.Dispatch('AutoCAD.Application')
app.Visible = True

def retry(fn):
    for attempt in range(20):
        try:
            return fn()
        except pythoncom.com_error:
            if attempt == 19:
                raise
            time.sleep(1)

doc = retry(lambda: app.Documents.Open(str(source)))
try:
    retry(lambda: doc.SaveAs(str(target)))
finally:
    retry(lambda: doc.Close(False))
print(target)

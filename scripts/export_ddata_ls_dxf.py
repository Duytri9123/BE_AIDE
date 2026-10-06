"""Export a read-only DXF copy of D:\\data's LS source DWG for block inspection."""
import time
from pathlib import Path
import pythoncom
import win32com.client

source=Path(r'D:\data\catalog_sources\ls_2026-10-01\LS-device-library.dwg')
target=Path(__file__).resolve().parents[2]/'BE_AIDE/tmp/ls-ddata-library.dxf'
try: app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception: app=win32com.client.Dispatch('AutoCAD.Application')
app.Visible=True
def retry(fn):
    for attempt in range(30):
        try: return fn()
        except pythoncom.com_error:
            if attempt==29: raise
            time.sleep(1)
doc=retry(lambda:app.Documents.Open(str(source)))
try:
    retry(lambda:doc.SaveAs(str(target),win32com.client.constants.ac2018_dxf))
finally:
    retry(lambda:doc.Close(False))
print(target)

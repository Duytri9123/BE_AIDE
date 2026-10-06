"""WBlock original placed TS1600 devices from the D:\\data source DWG."""
import time
from pathlib import Path
import pythoncom
import win32com.client

root=Path(__file__).resolve().parents[2]
source=Path(r'D:\data\catalog_sources\ls_2026-10-01\LS-device-library.dwg')
dest=root/'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI/native'
items=[('2320FC','LS-DATA-TS1600AF-3P'),('2320FD','LS-DATA-TS1600AF-4P')]
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
time.sleep(3)
try:
    for handle,stem in items:
        block=retry(lambda:doc.HandleToObject(handle))
        print('SOURCE',handle,block.Name,block.ObjectName,flush=True)
        selection=retry(lambda:doc.SelectionSets.Add('CODEX_DDATA_TS1600'))
        try:
            selection.AddItems(win32com.client.VARIANT(
                pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[block]))
            retry(lambda:doc.Wblock(str(dest/(stem+'.dwg')),selection))
        finally:
            retry(lambda:selection.Delete())
finally:
    retry(lambda:doc.Close(False))
for _,stem in items:
    cad=retry(lambda:app.Documents.Open(str(dest/(stem+'.dwg'))))
    try:
        retry(lambda:cad.SaveAs(str(dest/(stem+'.dxf')),
                                win32com.client.constants.ac2018_dxf))
    finally:
        retry(lambda:cad.Close(False))
    print('EXPORTED',stem,flush=True)

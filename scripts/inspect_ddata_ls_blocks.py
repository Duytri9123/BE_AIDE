r"""Read named TS1600 block placements from D:\data's LS DWG."""
import time
from pathlib import Path

import pythoncom
import win32com.client

source=Path(r'D:\data\catalog_sources\ls_2026-10-01\LS-device-library.dwg')
try: app=win32com.client.GetActiveObject('AutoCAD.Application')
except Exception: app=win32com.client.Dispatch('AutoCAD.Application')
app.Visible=True

def retry(fn):
    for attempt in range(20):
        try: return fn()
        except pythoncom.com_error:
            if attempt==19: raise
            time.sleep(1)

docs=retry(lambda:list(app.Documents))
doc=next((d for d in docs if Path(d.FullName).resolve()==source.resolve()),None)
opened=doc is None
if opened: doc=retry(lambda:app.Documents.Open(str(source)))
time.sleep(4)
try:
    for block in retry(lambda:list(doc.Blocks)):
        if not block.Name.startswith('*') and ('1600' in block.Name.upper() or '1250' in block.Name.upper()):
            print('BLOCK',block.Name,'entities',block.Count,flush=True)
            for entity in block:
                kind=entity.ObjectName
                if kind in ('AcDbText','AcDbMText'):
                    try: print(' TEXT',entity.TextString[:120],flush=True)
                    except AttributeError: pass
    for entity in retry(lambda:list(doc.ModelSpace)):
        if entity.ObjectName!='AcDbBlockReference': continue
        block=win32com.client.CastTo(entity,'IAcadBlockReference')
        name=retry(lambda:block.Name)
        if '1600' not in name.upper() and '1250' not in name.upper(): continue
        print('INSERT',block.Handle,name,'at',tuple(round(x,1) for x in block.InsertionPoint),flush=True)
        if block.HasAttributes:
            print(' ATTRS',[(a.TagString,a.TextString) for a in block.GetAttributes()],flush=True)
finally:
    if opened: retry(lambda:doc.Close(False))

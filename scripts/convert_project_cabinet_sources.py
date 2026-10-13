"""Read top-level project DWGs only; export copies, never save originals."""
import json,hashlib,time
from pathlib import Path
import win32com.client
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'BE_AIDE/tmp/project_cabinet_sources';OUT.mkdir(exist_ok=True)
app=win32com.client.GetActiveObject('AutoCAD.Application');rows=[];seen={}
def call(fn):
 for n in range(30):
  try:return fn()
  except Exception:
   if n==29:raise
   time.sleep(.5)
for source in sorted((ROOT/'Tudien').glob('*.dwg')):
 if 'THƯ VIỆN' in source.name.upper():continue
 digest=hashlib.sha256(source.read_bytes()).hexdigest();sid=digest[:16];folder=OUT/sid;folder.mkdir(exist_ok=True);target=folder/'drawing.dxf'
 row={'id':sid,'source_file':source.name,'sha256':digest,'dxf':str(target.relative_to(ROOT)).replace('\\','/'),'status':'pending'};doc=None
 try:
  if not target.exists():
   doc=call(lambda:app.Documents.Open(str(source.resolve()),True))
   call(lambda:doc.SaveAs(str(target.resolve()),65))
  row['status']='exported'
 except Exception as e:row['error']=str(e);row['status']='failed'
 finally:
  if doc:call(lambda:doc.Close(False))
 rows.append(row);(OUT/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(len(rows),source.name,row['status'],flush=True)
print('Sources',len(rows),'unique',len({r['id'] for r in rows}))

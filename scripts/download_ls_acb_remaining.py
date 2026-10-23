import sys,subprocess
from pathlib import Path
sys.path.insert(0,'scripts');from download_ls_full_pricebook_cad import download,OUT
ids=[419521,417821,417726,417732,417820,417774,417731,417736,417775,417779,420006,417740,417787,417795,420208,417753]
for uid in ids:
 for folder in download(uid):
  out=folder/'source.dxf'
  if not out.exists():
   s=folder/'convert.scr';s.write_text('FILEDIA\n0\n_.DXFOUT\n'+out.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
   with (folder/'convert.log').open('wb') as log:subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(folder/'source.dwg'),'/s',str(s),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  print(uid,folder.name,out.exists(),flush=True)

"""Download current official LS CAD, retaining file-list provenance and hashes."""
import urllib.request,urllib.parse,json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/LS/NguonBenNgoai'
IDS=[417152,420008,420010,420011,420012]
for uid in IDS:
 req=urllib.request.Request(f'https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id={uid}',headers={'Referer':'https://www.ls-electric.com/ko/download/','X-Requested-With':'XMLHttpRequest','User-Agent':'Mozilla/5.0'})
 files=json.loads(urllib.request.urlopen(req).read())['data']
 for f in files:
  if not f['df_name'].lower().endswith('.dwg') or (uid==417152 and f['df_id']>45195):continue
  folder=OUT/str(f['df_id']);folder.mkdir(parents=True,exist_ok=True);url='https://www.ls-electric.com'+urllib.parse.quote(f['df_path']);dwg=folder/'source.dwg'
  if not dwg.exists():
   data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.ls-electric.com/ko/download/'}),timeout=60).read();assert data.startswith(b'AC10');dwg.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'document_id':uid,'file':f,'source_url':url,'source_page':'https://www.ls-electric.com/ko/download/?k_word=Metasol','sha256':hashlib.sha256(dwg.read_bytes()).hexdigest(),'checked_at':'2026-10-20'},indent=2),encoding='utf8')
  dxf=folder/'source.dxf'
  if not dxf.exists():
   scr=folder/'convert.scr';scr.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
   with (folder/'convert.log').open('wb') as log:subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(dwg),'/s',str(scr),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  assert dxf.exists();print(f['df_id'],f['df_name'].encode('ascii','backslashreplace').decode(),flush=True)

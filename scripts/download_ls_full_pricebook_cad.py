"""Acquire official LS CAD across every missing pricebook category."""
import urllib.request,urllib.parse,json,hashlib,subprocess,zipfile,io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/LS/NguonBenNgoai'
IDS=[417804,417809,417799,417720,417164,420078,421281,418371,417429,420013,420016,420017,420018,421284,417803]
def download(uid):
 req=urllib.request.Request(f'https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id={uid}',headers={'Referer':'https://www.ls-electric.com/ko/download/','X-Requested-With':'XMLHttpRequest','User-Agent':'Mozilla/5.0'})
 files=json.loads(urllib.request.urlopen(req,timeout=45).read())['data'];result=[]
 for f in files:
  if not f['df_name'].lower().endswith(('.dwg','.zip')):continue
  if '3D CAD' in f['df_name']:continue
  folder=OUT/str(f['df_id']);folder.mkdir(parents=True,exist_ok=True);url='https://www.ls-electric.com'+urllib.parse.quote(f['df_path']);target=folder/('source.zip' if f['df_name'].lower().endswith('.zip') else 'source.dwg')
  if not target.exists():
   req=urllib.request.Request(url,headers={'Referer':'https://www.ls-electric.com/ko/download/','User-Agent':'Mozilla/5.0'});data=urllib.request.urlopen(req,timeout=60).read(60*1024*1024+1);assert len(data)<=60*1024*1024
   assert data.startswith(b'PK' if target.suffix=='.zip' else b'AC10');target.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'document_id':uid,'file':f,'source_url':url,'source_page':'https://www.ls-electric.com/ko/download/','sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checked_at':'2026-10-20'},indent=2),encoding='utf8')
  if target.suffix=='.zip':
   with zipfile.ZipFile(target) as archive:
    for index,name in enumerate(archive.namelist()):
     if not name.lower().endswith('.dwg'):continue
     entry=archive.getinfo(name);assert entry.file_size<60*1024*1024
     child=folder/f'drawing-{index:02}';child.mkdir(exist_ok=True);(child/'source.dwg').write_bytes(archive.read(name));(child/'source.json').write_text(json.dumps({'archive_member':name,'source_url':url,'package_sha256':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2),encoding='utf8');result.append(child)
  else:result.append(folder)
 return result
if __name__=='__main__':
 folders=[]
 with ThreadPoolExecutor(max_workers=3) as pool:
  for uid,result in zip(IDS,pool.map(download,IDS)):
   folders+=result;print('Downloaded document',uid,len(result),'drawings',flush=True)
 for folder in folders:
  dxf=folder/'source.dxf'
  if not dxf.exists():
   script=folder/'convert.scr';script.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
   with (folder/'convert.log').open('wb') as log:
    subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(folder/'source.dwg'),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  print('Converted',folder.relative_to(OUT),dxf.exists(),flush=True)

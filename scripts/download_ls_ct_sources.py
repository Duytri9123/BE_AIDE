import urllib.request,urllib.parse,json,hashlib,subprocess
from pathlib import Path
root=Path('data/CatalogTB/BienDong/LS/NguonBenNgoai');root.mkdir(parents=True,exist_ok=True)
for id in [417383,417380]:
 request=urllib.request.Request(f'https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id={id}',headers={'Referer':'https://www.ls-electric.com/ko/download/','X-Requested-With':'XMLHttpRequest','User-Agent':'Mozilla/5.0'})
 for f in json.loads(urllib.request.urlopen(request).read())['data']:
  folder=root/str(f['df_id']);folder.mkdir(exist_ok=True);url='https://www.ls-electric.com'+urllib.parse.quote(f['df_path'])
  data=dwg.read_bytes() if (dwg:=folder/'source.dwg').exists() else urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.ls-electric.com/ko/download/'}),timeout=60).read()
  assert data.startswith(b'AC10'),data[:100]
  dwg=folder/'source.dwg';dwg.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'document_id':id,'file':f,'source_url':url,'source_page':'https://www.ls-electric.com/ko/download/?k_word=ZCT' if id==417383 else 'https://www.ls-electric.com/ko/download/?k_word=3CT','sha256':hashlib.sha256(data).hexdigest(),'checked_at':'2026-10-20'},indent=2),encoding='utf8')
  dxf=(folder/'source.dxf').resolve();scr=folder/'convert.scr';scr.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
  if dxf.exists():
   print(f['df_id'],'already converted',flush=True);continue
  with (folder/'convert.log').open('wb') as log:
   result=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(dwg.resolve()),'/s',str(scr.resolve()),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  print(f['df_id'],len(data),dxf.exists(),flush=True)

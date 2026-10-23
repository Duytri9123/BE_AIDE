"""Discover and acquire official NXB-63 drawings from current manufacturer HTML."""
import hashlib,json,re,subprocess,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
PAGE='https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html'
def main():
 html=urllib.request.urlopen(PAGE,timeout=40).read().decode('utf8')
 links=list(dict.fromkeys(re.findall(r'href="([^"]*NXB-63-MCB-Drawing-[1-4]P-2D.dwg)"',html)))
 assert len(links)==4
 for href in links:
  pole=re.search(r'([1-4]P)-2D',href)[1];folder=CAT/'Chint/NguonBenNgoai'/('NXB-63-'+pole);folder.mkdir(parents=True,exist_ok=True)
  url=urllib.parse.urljoin(PAGE,href);dwg=folder/'source.dwg'
  if not dwg.exists():
   data=urllib.request.urlopen(url,timeout=45).read();assert data.startswith(b'AC10');dwg.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'source_url':url,'source_page':PAGE,'checked_at':'2026-10-22','sha256':hashlib.sha256(dwg.read_bytes()).hexdigest()},indent=2),encoding='utf8')
  dxf=folder/'source.dxf'
  if not dxf.exists():
   scr=folder/'convert.scr';scr.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
   with (folder/'convert.log').open('wb') as log:subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(dwg),'/s',str(scr),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
  assert dxf.exists();print(pole,'downloaded and converted',flush=True)
if __name__=='__main__':main()

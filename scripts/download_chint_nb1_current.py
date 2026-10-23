"""Acquire observed official NB1 IGES geometry and preserve native units."""
import hashlib,json,re,urllib.parse,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB'
PAGE='https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nb1-63h.html'
def main():
 html=urllib.request.urlopen(PAGE,timeout=40).read().decode('utf8');(ROOT/'tmp/chint-nb163h-current.html').write_text(html,encoding='utf8')
 links=list(dict.fromkeys(a['href'] for a in BeautifulSoup(html,'html.parser').select('a[href]') if a['href'].lower().endswith('.igs')))
 print(links,flush=True)
 for href in links:
  name=urllib.parse.unquote(href.rsplit('/',1)[-1]);match=re.search(r'NB1-63-([124]P)-3D',name)
  if not match:continue
  folder=CAT/'Chint/NguonBenNgoai'/('NB1-63H-'+match[1]);folder.mkdir(parents=True,exist_ok=True);target=folder/'source.igs'
  url=urllib.parse.urljoin(PAGE,urllib.parse.quote(urllib.parse.unquote(href),safe='/:'))
  if not target.exists():
   data=urllib.request.urlopen(url,timeout=90).read();assert len(data)>1000 and b'<' not in data[:50];target.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'source_url':url,'source_page':PAGE,'file_name':name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checked_at':'2026-10-22'},indent=2),encoding='utf8')
  print(match[1],target.stat().st_size,flush=True)
if __name__=='__main__':main()

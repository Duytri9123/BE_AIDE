"""Discover current CHINT NDK STEP links and catalogue; no inferred download URLs."""
import hashlib,json,re,urllib.parse,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/Chint/NguonBenNgoai'
PAGE='https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/ndk.html'
def main():
 html=urllib.request.urlopen(PAGE,timeout=40).read().decode('utf8');(ROOT/'tmp/chint-ndk-current.html').write_text(html,encoding='utf8')
 links=list(dict.fromkeys(a['href'] for a in BeautifulSoup(html,'html.parser').select('a[href]') if a['href'].lower().endswith(('.stp','.pdf'))))
 for href in links:
  name=urllib.parse.unquote(href.rsplit('/',1)[-1]);match=re.fullmatch(r'NDK-(\d+)-202403-Control Transformer-Drawing.stp',name)
  if not match and name!='NDK-Control Transformer-Catalog.pdf':continue
  ident='NDK-'+match[1] if match else 'NDK-CATALOG';folder=OUT/ident;folder.mkdir(parents=True,exist_ok=True);target=folder/('source.step' if match else 'source.pdf')
  url=urllib.parse.urljoin(PAGE,urllib.parse.quote(urllib.parse.unquote(href),safe='/:'))
  if not target.exists():
   data=urllib.request.urlopen(url,timeout=60).read();assert data.startswith(b'ISO-10303-21' if match else b'%PDF');target.write_bytes(data)
  (folder/'source.json').write_text(json.dumps({'source_url':url,'source_page':PAGE,'file_name':name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checked_at':'2026-10-22'},indent=2),encoding='utf8')
  print(ident,target.stat().st_size,flush=True)
if __name__=='__main__':main()

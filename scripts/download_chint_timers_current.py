"""Acquire observed manufacturer timer STEP and dimension catalogues."""
import hashlib,json,urllib.parse,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/Chint/NguonBenNgoai'
def main():
 for model in ['KG316T','NKG1']:
  page='https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/'+model.lower()+'.html'
  html=urllib.request.urlopen(page,timeout=40).read().decode('utf8')
  links=list(dict.fromkeys(a['href'] for a in BeautifulSoup(html,'html.parser').select('a[href]') if a['href'].lower().endswith(('.stp','.pdf'))))
  folder=OUT/model;folder.mkdir(parents=True,exist_ok=True)
  for href in links:
   filename=urllib.parse.unquote(href.rsplit('/',1)[-1]);is_step=filename.lower().endswith('.stp')
   if not is_step and 'catalog' not in filename.lower():continue
   dest=folder/('source.step' if is_step else 'catalog.pdf');url=urllib.parse.urljoin(page,urllib.parse.quote(urllib.parse.unquote(href),safe='/:'))
   if not dest.exists():
    data=urllib.request.urlopen(url,timeout=60).read();assert data.startswith(b'ISO-10303-21' if is_step else b'%PDF');dest.write_bytes(data)
   meta={'source_url':url,'source_page':page,'file_name':filename,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'checked_at':'2026-10-22'}
   (folder/('source.json' if is_step else 'catalog-source.json')).write_text(json.dumps(meta,indent=2),encoding='utf8');print(model,filename,dest.stat().st_size,flush=True)
if __name__=='__main__':main()

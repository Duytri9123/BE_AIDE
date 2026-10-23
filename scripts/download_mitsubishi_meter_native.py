"""Collect exact priced meter/sensor native CAD; no unreviewed file is published."""
import concurrent.futures,hashlib,io,json,re,urllib.parse,urllib.request,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'data/CatalogTB/Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
PAGES=[
 'https://www.mitsubishielectric.com/fa/download/cad/search.page?mode=cad&kisyu=/pmd',
 'https://www.mitsubishielectric.com/fa/download/cad/search.page?mode=cad&kisyu=/ems',
 'https://www.mitsubishielectric.com/fa/sg_en/download/cad/search.page?kisyu=%2Fems&mode=cad',
 'https://www.mitsubishielectric.com/fa/download/cad/search.page?category1=18&categoryb1=&categoryb2=&categoryb3=&categoryb4=&kisyu=%2Fems&mode=cad',
 'https://www.mitsubishielectric.com/fa/download/cad/search.page?category1=23&category2=&category3=&category4=&kisyu=%2Fems&mode=cad',
]

def fetch(item):
 folder=SRC/('NATIVE2D-'+Path(item['file_name']).stem);folder.mkdir(exist_ok=True)
 archive=folder/'original.zip'
 if not archive.exists() or not zipfile.is_zipfile(archive):
  data=urllib.request.urlopen(item['source_url'],timeout=50).read()
  assert zipfile.is_zipfile(io.BytesIO(data)),'Download is not native CAD archive'
  archive.write_bytes(data)
 data=archive.read_bytes();z=zipfile.ZipFile(io.BytesIO(data));files=[]
 for info in z.infolist():
  if not info.filename.lower().endswith(('.dxf','.dwg','.step','.stp','.igs','.iges')):continue
  dest=folder/Path(info.filename.replace('\\','/')).name
  body=z.read(info);dest.write_bytes(body);files.append({'name':dest.name,'sha256':hashlib.sha256(body).hexdigest()})
 assert files,item['file_name']
 item.update(archive_sha256=hashlib.sha256(data).hexdigest(),files=files,publication_status='held_pending_native_view_review')
 (folder/'source.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf8')
 print(item['models'],len(files),'native files',flush=True);return item

def main():
 rows=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r['brand']=='Mitsubishi Electric' and r['category']=='METER']
 by_model={}
 for r in rows:by_model.setdefault(re.sub(r'\(\*\)$','',r['item_name']).upper(),[]).append(r['id'])
 grouped={};errors=[]
 for i,url in enumerate(PAGES):
  try:
   b=urllib.request.urlopen(url,timeout=45).read();(SRC/f'meter-native-index-{i}.html').write_bytes(b)
   s=BeautifulSoup(b,'html.parser')
   for table in s.select('table'):
    models=[]
    for tr in table.select('tr'):
     cells=[c.get_text(' ',strip=True).upper() for c in tr.find_all('td',recursive=False)[:3]]
     named=[]
     for cell in cells:
      text=re.sub(r'\s+\(INCLUDES OPTIONAL MODULES\)$','',cell)
      if re.fullmatch(r'(?:EMU|ME|MES|CZ)[A-Z0-9_-]+(?:\s+(?:EMU|ME|MES|CZ)[A-Z0-9_-]+)*',text):named.extend(text.split())
     if named:models=[c for c in named if c in by_model]
     if not models:continue
     for a in tr.select('a[href]'):
      if not a['href'].lower().endswith('.zip'):continue
      link=urllib.parse.urljoin(url,a['href'])
      if '/members/' in urllib.parse.urlsplit(link).path:
       errors.append({'source_url':link,'error':'Membership-only download; not fetched'});continue
      if link not in grouped:grouped[link]={'source_page':url,'source_url':link,'source_row':tr.get_text(' ',strip=True),'file_name':link.rsplit('/',1)[-1],'models':[],'price_row_ids':[]}
      g=grouped[link];g['models']=sorted(set(g['models']+models));g['price_row_ids']=sorted(set(g['price_row_ids']+[rid for m in models for rid in by_model[m]]))
  except Exception as e:errors.append({'source_page':url,'error':str(e)})
 done=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={pool.submit(fetch,item):item for item in grouped.values()}
  for f,item in jobs.items():
   try:done.append(f.result())
   except Exception as e:errors.append({'source_url':item['source_url'],'error':str(e)})
 (SRC/'meter-native-downloads.json').write_text(json.dumps({'downloaded':done,'errors':errors},ensure_ascii=False,indent=2),encoding='utf8')
 print('Downloaded',len(done),'exact price rows',len({r for x in done for r in x['price_row_ids']}),'errors',len(errors),flush=True)
if __name__=='__main__':main()

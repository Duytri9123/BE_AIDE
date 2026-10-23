"""Discover manufacturer contactor/overload CAD for exact named price families."""
import json,re,urllib.request,urllib.parse,concurrent.futures,zipfile,io,hashlib
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'data/CatalogTB/Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
BASE='https://www.mitsubishielectric.com'
rows=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r['brand']=='Mitsubishi Electric']

def scan(html,url,kind):
 out=[]
 for table in BeautifulSoup(html,'html.parser').select('table'):
  model=''
  for tr in table.select('tr'):
   td=tr.find_all('td',recursive=False)
   # MS-N adds an AC/DC column before the model name; do not carry the
   # operating-mode heading as a model or attach its files to the prior model.
   candidates=[c.get_text(' ',strip=True) for c in td[:2]]
   named=[c for c in candidates if re.fullmatch(r'[A-Z]{1,4}-[A-Z0-9][A-Z0-9×()/_-]*',c)]
   if named:model=named[-1]
   for a in tr.select('a[href]'):
    if not a['href'].lower().endswith('_step.zip'):continue
    matches=[r for r in rows if r['category']==kind and re.match(re.escape(model)+r'(?=$|\s|/)',r['item_name'],re.I)]
    if not matches:continue
    out.append({'model':model,'models':[model],'kind':kind,'source_url':urllib.parse.urljoin(BASE,a['href']),'source_page':url,'file_name':a['href'].rsplit('/',1)[-1],'price_row_ids':[r['id'] for r in matches],'source_row':tr.get_text(' ',strip=True)})
 return out

def fetch(item):
 folder=SRC/Path(item['file_name']).stem;folder.mkdir(exist_ok=True)
 if not (folder/'source.step').exists():
  data=urllib.request.urlopen(item['source_url'],timeout=40).read();z=zipfile.ZipFile(io.BytesIO(data));names=[n for n in z.namelist() if n.lower().endswith(('.step','.stp'))];assert len(names)==1,names
  (folder/'original.zip').write_bytes(data);(folder/'source.step').write_bytes(z.read(names[0]))
 item['step_sha256']=hashlib.sha256((folder/'source.step').read_bytes()).hexdigest()
 (folder/'source.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf8')
 print(item['file_name'],item['models'],len(item['price_row_ids']),flush=True);return item

def main():
 initial=(ROOT/'tmp/mitsubishi-contactor-index.html').read_bytes();s=BeautifulSoup(initial,'html.parser')
 pages={BASE+'/fa/download/cad/search.page?category1=2&categoryb1=2&kisyu=%2Flvsw&mode=cad':('CONTACTOR',initial)}
 for a in s.select('a[href]'):
  text=a.get_text(' ',strip=True);href=a['href']
  if text not in {'Thermal Overload Relays','MS-N Series','Non-Reversible Type (DC Operated)'}:continue
  url=BASE+'/fa/download/cad/search.page?'+urllib.parse.urlsplit(href).query
  kind='THERMAL_RELAY' if text=='Thermal Overload Relays' else 'CONTACTOR'
  html=urllib.request.urlopen(url,timeout=45).read();pages[url]=(kind,html)
 grouped={}
 for i,(url,(kind,html)) in enumerate(pages.items()):
  (SRC/f'switchgear-index-{i}.html').write_bytes(html)
  for item in scan(html,url,kind):
   key=item['source_url']
   if key not in grouped:grouped[key]=item
   else:
    d=grouped[key];d['models']=sorted(set(d['models']+item['models']));d['price_row_ids']=sorted(set(d['price_row_ids']+item['price_row_ids']))
 done=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={pool.submit(fetch,x):x for x in grouped.values()}
  for f,item in jobs.items():
   try:done.append(f.result())
   except Exception as e:errors.append({'item':item,'error':str(e)})
 (SRC/'switchgear-downloads.json').write_text(json.dumps({'downloaded':done,'errors':errors},ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',len(done),'errors',len(errors),flush=True)
if __name__=='__main__':main()

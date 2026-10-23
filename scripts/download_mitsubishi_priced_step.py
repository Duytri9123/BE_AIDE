"""Discover actual manufacturer STEP links and match exact named price families."""
import concurrent.futures,hashlib,io,json,re,sys,urllib.request,urllib.parse,zipfile
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.services.catalog_family_matching import row_poles
OUT=ROOT/'data/CatalogTB/Mitsubishi/NguonBenNgoai/PRIMARY-20261022'
ROWS=[r for r in json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'] if r['brand'].lower().startswith('mitsubishi')]
BASE='https://www.mitsubishielectric.com'
def parse(html,page,kind):
 results=[];s=BeautifulSoup(html,'html.parser')
 for table in s.select('table'):
  model=''
  for tr in table.select('tr'):
   td=tr.find_all('td',recursive=False)
   if td and td[0].get_text(' ',strip=True):model=td[0].get_text(' ',strip=True)
   for a in tr.select('a[href]'):
    if '.zip' not in a['href'] or '3D CAD' not in tr.get_text():continue
    name=a['href'].rsplit('/',1)[1];m=re.search(r'_([1-4])p(?:[_.])',name,re.I)
    pole_label=re.search(r'(?<![A-Z0-9])([1-4])P(?:\+N)?',tr.get_text(' ',strip=True),re.I)
    poles=pole_label[0].upper() if pole_label else m[1]+'P' if m else None
    matches=[r for r in ROWS if poles and row_poles(r)==poles and re.match(re.escape(model)+r'(?=$|\s|/)',str(r['item_name']),re.I)]
    if kind=='ACB':
     mounting='FIX' if '_fix' in name.lower() else 'DR' if '_dr' in name.lower() else None
     matches=[r for r in matches if mounting and re.search(r'\b'+mounting+r'\b',r['item_name'],re.I)]
    frame=re.match(r'N[FV](\d+)',model,re.I)
    if frame:matches=[r for r in matches if float((r.get('specifications') or {}).get('In (A)') or 0)<=int(frame[1])]
    if model in {'BH-D6','BH-D10','BH-D10 DC','BH-DN'}:matches=[r for r in matches if float((r.get('specifications') or {}).get('In (A)') or 0)<=63]
    if model.startswith(('NF63-','NV63-')) and '_m' in name.lower():
     m8='_m8' in name.lower();matches=[r for r in matches if (float((r.get('specifications') or {}).get('In (A)') or 0)>50)==m8]
    results.append({'model':model,'poles':poles,'kind':kind,'source_url':urllib.parse.urljoin(BASE,a['href']),'source_page':page,'file_name':name,'price_row_ids':[r['id'] for r in matches],'source_row':tr.get_text(' ',strip=True)})
 return results
def fetch(item):
 if not item['price_row_ids']:return None
 p=OUT/Path(item['file_name']).stem;p.mkdir(parents=True,exist_ok=True)
 if not (p/'source.step').exists():
  data=urllib.request.urlopen(item['source_url'],timeout=40).read();z=zipfile.ZipFile(io.BytesIO(data));files=[n for n in z.namelist() if n.lower().endswith(('.step','.stp'))];assert len(files)==1,files
  (p/'original.zip').write_bytes(data);(p/'source.step').write_bytes(z.read(files[0]));item['original_step_name']=files[0]
 item['step_sha256']=hashlib.sha256((p/'source.step').read_bytes()).hexdigest();(p/'source.json').write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding='utf8');print(item['model'],item['poles'],len(item['price_row_ids']),p.name,flush=True);return item
def main():
 OUT.mkdir(parents=True,exist_ok=True);initial=(ROOT/'tmp/mitsubishi-cad-index.html').read_bytes();discovered=parse(initial,BASE+'/fa/download/cad/search.page?category1=102&kisyu=%2Flvcb&mode=cad','MCCB');s=BeautifulSoup(initial,'html.parser')
 for cid,kind in [('101','ACB'),('103','ELCB'),('108','MCB')]:
  a=next(a for a in s.select('a[href]') if 'category1='+cid+'&' in a['href']);url=BASE+'/fa/download/cad/search.page?'+urllib.parse.urlsplit(a['href']).query;html=urllib.request.urlopen(url,timeout=40).read();(OUT/('index-'+cid+'.html')).write_bytes(html);discovered+=parse(html,url,kind)
 (OUT/'discovered.json').write_text(json.dumps(discovered,ensure_ascii=False,indent=2),encoding='utf8');grouped={}
 for x in discovered:
  if not x['price_row_ids']:continue
  key=(x['source_url'],x['kind'])
  if key not in grouped:grouped[key]={**x,'models':[],'price_row_ids':[]}
  target=grouped[key];target['models']=sorted(set(target['models']+[x['model']]));target['price_row_ids']=sorted(set(target['price_row_ids']+x['price_row_ids']))
 selected=list(grouped.values());print('Discovered',len(discovered),'priced source bodies',len(selected),flush=True)
 errors=[];done=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  tasks={pool.submit(fetch,x):x for x in selected}
  for f in concurrent.futures.as_completed(tasks):
   try:done.append(f.result())
   except Exception as e:errors.append({'source':tasks[f],'error':str(e)});print('HELD',tasks[f]['file_name'],str(e),flush=True)
 (OUT/'downloads.json').write_text(json.dumps({'downloaded':done,'errors':errors},ensure_ascii=False,indent=2),encoding='utf8');print('Complete',len(done),'errors',len(errors),flush=True)
if __name__=='__main__':main()

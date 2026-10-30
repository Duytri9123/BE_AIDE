"""Acquire only observed public CHINT CAD links; downloads are not publications."""
import hashlib,json,re,urllib.request,urllib.parse,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'data/CatalogTB/Chint/NguonBenNgoai/PRIMARY-RECHECK-20261023'

def main():
 BASE.mkdir(exist_ok=True);jobs=[]
 for line in ['nm8n','nxc','nxr']:
  file=ROOT/f'tmp/chint-{line}-recheck-links.json'
  if not file.exists():continue
  page=f'https://www.chintglobal.com/global/en/products/low-voltage/iec/'+('secondary-power-distribution/' if line=='nm8n' else 'industrial-control/')+line+'.html'
  for href in json.loads(file.read_text(encoding='utf8')):
   name=urllib.parse.unquote(href.rsplit('/',1)[-1])
   if not name.lower().endswith(('.stp','.step')):continue
   if line=='nm8n' and not (name.startswith('NM8N-MCCB-Drawing-') or name.startswith(('NM8N-AX21','NM8N-SHT21','NM8N-SHT22','NM8N-UVT26'))):continue
   url=urllib.parse.urljoin(page,urllib.parse.quote(urllib.parse.unquote(href),safe='/:,()-'))
   ident=re.sub(r'[^A-Za-z0-9-]+','-',Path(name).stem).strip('-')
   jobs.append({'model_source_name':name,'source_page':page,'source_url':url,'folder':ident,'status':'pending'})
 def fetch(job):
  try:
   folder=BASE/job['folder'];folder.mkdir(exist_ok=True);p=folder/'source.step'
   if not p.exists():
    data=urllib.request.urlopen(job['source_url'],timeout=75).read();assert data.lstrip().startswith(b'ISO-10303-21;') and len(data)>1000
    p.write_bytes(data)
   job.update(step_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,status='native_downloaded_review_pending',checked_at='2026-10-23')
   metadata=folder/'source.json';previous=json.loads(metadata.read_text(encoding='utf8')) if metadata.exists() else {}
   preserved=previous if previous.get('step_sha256')==job['step_sha256'] and previous.get('source_url')==job['source_url'] else {}
   metadata.write_text(json.dumps({**preserved,**job},ensure_ascii=False,indent=2),encoding='utf8')
  except Exception as e:job.update(status='download_failed',error=str(e))
  print(job['model_source_name'],job['status'],flush=True);return job
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(fetch,jobs))
 (BASE/'downloads.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
 print('Downloaded',sum(j['status']=='native_downloaded_review_pending' for j in results),'of',len(results),flush=True)

if __name__=='__main__':main()

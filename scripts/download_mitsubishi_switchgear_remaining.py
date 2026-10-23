"""Read extra model columns and actual manufacturer navigation for N/SQ variants."""
import json,urllib.request,urllib.parse,concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
from download_mitsubishi_switchgear_step import ROOT,SRC,BASE,scan,fetch

def main():
 old={x['source_url'] for name in ['downloads.json','switchgear-downloads.json','protector-downloads.json','drawout-downloads.json','mcb-remaining-downloads.json'] for x in json.loads((SRC/name).read_text(encoding='utf8'))['downloaded']}
 pages=[]
 nav=BeautifulSoup((SRC/'switchgear-index-0.html').read_bytes(),'html.parser')
 nlink=next(a for a in nav.select('a[href]') if a.get_text(' ',strip=True)=='MS-N Series')
 nurl=BASE+'/fa/download/cad/search.page?'+urllib.parse.urlsplit(nlink['href']).query
 pages.append((nurl,'CONTACTOR',(SRC/'switchgear-index-2.html').read_bytes()))
 for name,kind,text in [('switchgear-index-0.html','CONTACTOR','With Spring Clamp Terminals'),('switchgear-index-1.html','THERMAL_RELAY','MS-N Series')]:
  s=BeautifulSoup((SRC/name).read_bytes(),'html.parser');a=next(a for a in s.select('a[href]') if a.get_text(' ',strip=True)==text)
  url=BASE+'/fa/download/cad/search.page?'+urllib.parse.urlsplit(a['href']).query
  b=urllib.request.urlopen(url,timeout=45).read();(SRC/('remaining-'+kind+'.html')).write_bytes(b);pages.append((url,kind,b))
 grouped={}
 for url,kind,html in pages:
  for x in scan(html,url,kind):
   if x['source_url'] in old:continue
   key=x['source_url']
   if key not in grouped:grouped[key]=x
   else:
    d=grouped[key];d['models']=sorted(set(d['models']+x['models']));d['price_row_ids']=sorted(set(d['price_row_ids']+x['price_row_ids']))
 done=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={pool.submit(fetch,x):x for x in grouped.values()}
  for f,x in jobs.items():
   try:done.append(f.result())
   except Exception as e:errors.append({'item':x,'error':str(e)})
 (SRC/'switchgear-remaining-downloads.json').write_text(json.dumps({'downloaded':done,'errors':errors},ensure_ascii=False,indent=2),encoding='utf8')
 print('Complete',len(done),'errors',len(errors),'price rows',len({r for x in done for r in x['price_row_ids']}),flush=True)
if __name__=='__main__':main()

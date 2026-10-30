"""Save current public LS download listings for the unresolved coverage queue."""
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from research_ls_america_sources import fetch, HOST, ROOT

QUERIES=['Susol','DH1','Metasol MCCB','GIMAC','BK','LA63','MR-8','MC-150']

def search(q):
    url=HOST+'/api/v1/fo/download-center/contents?'+urllib.parse.urlencode(dict(q=q,size=100,page=0,includeFileContent='true'))
    d=json.loads(fetch(url))
    path=ROOT/'docs/ls-all-cad-2026-10-24/research-gap-20261025'
    path.mkdir(exist_ok=True)
    (path/(q.replace(' ','-')+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
    print(q,d['totalElements'],flush=True)
    for row in d['content']:
        if row['docType']!='D':continue
        print(q,row['title'],[(f['fileId'],f['fileName']) for v in row['versions'] for f in v['files']],flush=True)

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(search,QUERIES))

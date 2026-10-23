"""Acquire original LS STEP and 3D packages without substituting CAD families."""
import json,urllib.request,urllib.parse,hashlib,zipfile,io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/CatalogTB/LS/NguonBenNgoai'
HEAD={'Referer':'https://www.ls-electric.com/ko/download/','X-Requested-With':'XMLHttpRequest','User-Agent':'Mozilla/5.0'}
def acquire(entry):
 uid,f=entry;p=OUT/str(f['df_id']);p.mkdir(exist_ok=True,parents=True);ext=Path(f['df_name']).suffix.lower();target=p/('source.zip' if ext=='.zip' else 'source.step');url='https://www.ls-electric.com'+urllib.parse.quote(f['df_path'])
 valid=target.exists() and (zipfile.is_zipfile(target) if ext=='.zip' else b'END-ISO-10303-21' in target.read_bytes()[-500:])
 if not valid:
  b=urllib.request.urlopen(urllib.request.Request(url,headers=HEAD),timeout=90).read(150*1024*1024+1);assert len(b)<=150*1024*1024;temporary=target.with_suffix(target.suffix+'.part');temporary.write_bytes(b);temporary.replace(target)
 meta={'document_id':uid,'file':f,'source_url':url,'source_page':'https://www.ls-electric.com/ko/download/','sha256':hashlib.sha256(target.read_bytes()).hexdigest()};(p/'source.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
 paths=[]
 if ext=='.zip':
  with zipfile.ZipFile(target) as z:
   for i,n in enumerate(z.namelist()):
    if Path(n).suffix.lower() not in ['.step','.stp']:continue
    assert z.getinfo(n).file_size<150*1024*1024;d=p/f'model-{i:03}';d.mkdir(exist_ok=True);data=z.read(n);assert b'ISO-10303-21' in data[:100];(d/'source.step').write_bytes(data);(d/'source.json').write_text(json.dumps({**meta,'archive_member':n,'step_sha256':hashlib.sha256(data).hexdigest()},indent=2),encoding='utf8');paths.append(d)
 else:
  assert b'ISO-10303-21' in target.read_bytes()[:100];paths=[p]
 print(f['df_id'],ascii(f['df_name']),len(paths),'STEP',flush=True);return paths
if __name__=='__main__':
 entries=[]
 for d in json.loads((ROOT/'tmp/ls-current-source-files.json').read_text()):
  for f in d['files']:
   if f['df_name'].lower().endswith(('.stp','.step')) or f['df_id'] in [45226,55731]:entries.append((d['document_id'],f))
 with ThreadPoolExecutor(max_workers=3) as pool:
  for _ in pool.map(acquire,entries):pass

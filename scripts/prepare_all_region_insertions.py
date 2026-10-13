"""Prepare native REGION curves for all affected insertions, preserving originals."""
import json,os,subprocess,hashlib,shutil,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];OUT=BASE.parent/'outputs/catalogtb-linework-audit';W=BASE/'tmp/accessory_source_review'
sys.stdout.reconfigure(encoding='utf8')
rows=[r for r in json.loads((OUT/'audit.json').read_text(encoding='utf8'))['views'] if r.get('entity_types',{}).get('REGION')]
dest=OUT/'insertion-outlines';dest.mkdir(exist_ok=True)
jobs=OUT/'all-region-insert-jobs.txt'
jobs.write_text('\n'.join(r['path']+'\t'+str(dest/(hashlib.sha1(r['path'].encode()).hexdigest()+'.dxf')) for r in rows),encoding='utf8')
hashes={r['path']:hashlib.sha256(Path(r['path']).read_bytes()).hexdigest() for r in rows}
env=os.environ.copy();env['AIDE_PREVIEW_JOBS']=str(jobs)
with (OUT/'all-region-insert.log').open('wb') as log:
 subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(W/'input.dwg'),'/s',str(W/'regions.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
results=[]
for r in rows:
 source=Path(r['path']);converted=dest/(hashlib.sha1(r['path'].encode()).hexdigest()+'.dxf')
 count=int(converted.with_suffix('.dxf.count').read_text())
 assert count==r['entity_types']['REGION'],(r['view'],count,r['entity_types']['REGION'])
 assert hashes[r['path']]==hashlib.sha256(source.read_bytes()).hexdigest()
 target=source.with_name('ban_ve_net.dxf');shutil.copy2(converted,target)
 marker=source.with_name('native_preview.json')
 meta=json.loads(marker.read_text(encoding='utf8')) if marker.exists() else {}
 meta.update(insertion_outline=target.name,source_sha256=hashes[r['path']],outline_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),insertion_regions_converted=count)
 marker.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 results.append({'profile':r['profile'],'view':r['view'],'regions_converted':count,'source_unchanged':True})
(OUT/'all-region-insertions.json').write_text(json.dumps({'views':len(results),'regions':sum(r['regions_converted'] for r in results),'results':results},ensure_ascii=False,indent=2),encoding='utf8')
print('Prepared',len(results),'CAD views; converted',sum(r['regions_converted'] for r in results),'REGION objects',flush=True)

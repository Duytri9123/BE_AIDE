"""Render unsupported REGION edges natively; preserve every source DXF."""
import json, os, re, shutil, subprocess, sys, hashlib
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
sys.stdout.reconfigure(encoding='utf8')
base=Path(__file__).resolve().parents[1];root=base/'data/CatalogTB'
out=base.parent/'outputs/catalogtb-linework-audit';w=base/'tmp/accessory_source_review'
rows=[r for r in json.loads((out/'audit.json').read_text(encoding='utf8'))['views'] if 'REGION_WITHOUT_NATIVE_PREVIEW' in r['findings']]
job=out/'region-jobs.txt'
job.write_text('\n'.join(r['path']+'\t'+str(out/(r['view']+'-native-preview.dxf')) for r in rows),encoding='utf8')
env=os.environ.copy();env['AIDE_PREVIEW_JOBS']=str(job)
with (out/'region-export.log').open('wb') as log:
 subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(w/'input.dwg'),'/s',str(w/'regions.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
results=[]
for r in rows:
 folder=Path(r['path']).parent;target=out/(r['view']+'-native-preview.dxf')
 original_hash=hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()
 doc=ezdxf.readfile(target)
 assert not any(e.dxftype()=='REGION' for b in doc.blocks for e in b)
 for block in doc.blocks:
  for mask in list(block.query('WIPEOUT')):block.delete_entity(mask)
 backend=SVGBackend();Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
 before=folder/'xem_truoc.svg';backup=out/'before'/r['view'];backup.mkdir(parents=True,exist_ok=True)
 if before.exists():shutil.copy2(before,backup/'xem_truoc.svg')
 before.write_text(svg,encoding='utf8')
 companion=folder.parent.parent/'HinhChieu'/r['view']/'xem_truoc.svg'
 if companion.parent.exists():shutil.copy2(before,companion)
 p=root/r['profile'];data=json.loads(p.read_text(encoding='utf8'))
 if data.get('cad_chen_tu',{}).get('id_hinh_goc')==r['view']:shutil.copy2(before,p.parent/'CadChenTu/xem_truoc.svg')
 count=int(target.with_suffix('.dxf.count').read_text())
 derived=folder/'ban_ve_net.dxf';shutil.copy2(target,derived)
 (folder/'native_preview.json').write_text(json.dumps({'renderer':'AutoCAD REGION outlines','regions':count,'download_geometry_unchanged':True,'insertion_outline':derived.name,'source_sha256':original_hash,'outline_sha256':hashlib.sha256(derived.read_bytes()).hexdigest()}),encoding='utf8')
 assert original_hash==hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()
 results.append({'profile':r['profile'],'name':r['name'],'view':r['view'],'regions_converted':count,'original_dxf_unchanged':True})
(out/'repairs.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(results,ensure_ascii=False),flush=True)

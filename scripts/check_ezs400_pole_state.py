"""Re-export EZS400 native states for comparison; never invent device strokes."""
import os, subprocess, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8')
base=Path(__file__).resolve().parents[1]
w=base/'tmp/accessory_source_review'
out=base.parent/'outputs/ezs400-line-review';out.mkdir(exist_ok=True)
rows=[r for r in json.loads((w/'front-state-jobs.json').read_text(encoding='utf8')) if 'EZS400' in r['profile']]
jobs=out/'state-jobs.txt'
jobs.write_text('\n'.join(r['handle']+'\t'+r['option']+'\t'+str(out/(r['view']+'.dxf')) for r in rows),encoding='utf8')
env=os.environ.copy();env['AIDE_STATE_JOBS']=str(jobs)
with (out/'export.log').open('wb') as log:
 p=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(w/'input.dwg'),'/s',str(w/'states.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
for r in rows:
 target=out/(r['view']+'.dxf')
 assert target.with_suffix('.dxf.ok').exists(),target
print('Exported',len(rows),'synchronized states')
preview=out/'preview-jobs.txt'
preview.write_text('\n'.join(str(out/(r['view']+'.dxf'))+'\t'+str(out/(r['view']+'-preview.dxf')) for r in rows),encoding='utf8')
env['AIDE_PREVIEW_JOBS']=str(preview)
with (out/'preview.log').open('wb') as log:
 subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(w/'input.dwg'),'/s',str(w/'regions.scr'),'/l','en-US'],env=env,stdout=log,stderr=log,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
import ezdxf
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
import re
for r in rows:
 doc=ezdxf.readfile(out/(r['view']+'-preview.dxf'))
 for b in doc.blocks:
  for mask in list(b.query('WIPEOUT')):b.delete_entity(mask)
 backend=SVGBackend()
 Frontend(RenderContext(doc),backend).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=re.sub(r'(stroke-width: )(\d+)',lambda m:m[1]+str(max(1500,int(m[2]))),backend.get_string(Page(0,0)))
 (out/(r['view']+'.svg')).write_text(svg,encoding='utf8')
print('Rendered native comparison images',flush=True)
report={'device':'EZS400','status':'unresolved_visible_geometry_defect',
 'options_and_poles_exporter_corrected':True,
 'corrected_export_still_sparse':True,
 'native_dwg_full_geometry_equivalence_verified':False,
 'library_CAD_replaced':False,
 'finding':'Corrected 4P native export still has invisible nested INSERTs; enabling every hidden entity would mix alternative projections.',
 'next_required_check':'Compare supplier block in native AutoCAD with an approved complete front view before restoring missing geometry.'}
(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

import sys,json,io,hashlib,collections,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from app.services.cad.ls_colored_views import colored_dxf
from app.services.cad.ls_native_visibility import device_visibility_dxf
from app.services.cad.device_block_export import native_visibility_insert
from app.services.cad.ls_view_coverage import view_coverage
from app.api.v1.endpoints.equipment_library import view_dxf,view_preview
from app.services.catalogtb_browser import browser_data
from app.services.customer_equipment_information import public_view_id
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/chint-audit-2026-10-26';audit=json.loads((OUT/'audit-after.json').read_text(encoding='utf8'));devices={d['id']:d for d in browser_data()['items']};face_report=[];sets=[]
export=OUT/'exports-final';export.mkdir(exist_ok=True)
def without_rgb(data):
 lines=io.BytesIO(data).readlines();return b''.join(b''.join(lines[i:i+2]) for i in range(0,len(lines),2) if lines[i].strip()!=b'420')
for d in audit['devices']:
 for v in d['views']:
  source=Path(v['path']);raw=source.read_bytes();painted=colored_dxf(raw);assert without_rgb(raw)==without_rgb(painted);doc=ezdxf.read(io.StringIO(painted.decode('utf-8-sig'),newline=None));assert doc.units==4 and not doc.audit().errors;assert hashlib.sha256(source.read_bytes()).hexdigest()==v['sha256']
  face_report.append({'catalog_id':d['id'],'view_id':v['id'],'source_sha256':v['sha256'],'only_rgb_tags_changed':True,'source_unchanged':True})
 if any(s['complete'] for s in d['view_sets']):
  device=devices[d['id']];view=device['views'][0];res=view_dxf(d['id'],public_view_id(view['id']));doc=ezdxf.read(io.StringIO(res.body.decode('utf-8-sig'),newline=None));assert native_visibility_insert(doc) and not doc.audit().errors
  ref=next(iter(doc.modelspace()));assert ref.dxf.name.startswith('CHINT_');block=doc.blocks[ref.dxf.name];assert len(block)==6 and sum(not e.dxf.invisible for e in block)==1
  record=block.block_record;graph=record.extension_dict.dictionary['ACAD_ENHANCEDBLOCK'];nodes=[doc.entitydb[t.value] for sub in graph.xtags.subclasses for t in sub if t.code==360];parameter=next(n for n in nodes if n.dxftype()=='BLOCKVISIBILITYPARAMETER');states=[t.value for sub in parameter.xtags.subclasses for t in sub if t.code==303];assert set(states)=={'FRONT','REAR','SIDE-L','SIDE','TOP','BOTTOM'}
  file=export/(d['id']+'.dxf');file.write_bytes(res.body);dwg=file.with_suffix('.dwg');script=file.with_suffix('.scr');script.write_text('FILEDIA\n0\n_.AUDIT\n_Yes\n_.-WBLOCK\n'+dwg.as_posix()+'\n*\n_.QUIT\n_Yes\n',encoding='ascii')
  with file.with_suffix('.log').open('wb') as log:subprocess.run([r'C:\Program Files\Autodesk\AutoCAD 2022\accoreconsole.exe','/i',str(file),'/s',str(script),'/l','en-US'],stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  log=file.with_suffix('.log').read_text(encoding='utf-16-le',errors='replace');assert 'Total errors found 0 fixed 0' in log,(d['id'],'AutoCAD audit failed')
  sets.append({'catalog_id':d['id'],'model':d['model'],'states':states,'native_visibility':True,'autocad_audit':'0 errors / 0 fixes','one_initial_visible_face':True,'file':str(file.relative_to(OUT))})
 print('VERIFIED',len(face_report),'faces,',len(sets),'complete sets',flush=True)
(OUT/'colour-export-validation.json').write_text(json.dumps({'faces':len(face_report),'complete_visibility_sets':len(sets),'source_geometry_controls_layers_units_unchanged':True,'items':face_report,'sets':sets},ensure_ascii=False,indent=2),encoding='utf8');print('ALL PASS',len(face_report),len(sets),flush=True)

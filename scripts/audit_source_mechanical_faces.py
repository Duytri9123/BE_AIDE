"""Restore source hardware and horizontal faces; report every source face."""
import ast,json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf import dynblkhelper
from ezdxf.addons import Importer
from extract_project_helpers import ROOT,OUT,save,inside,bounds
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
# Load helpers without executing the old whole-window restoration pass.
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
HARDWARE=re.compile(r'HL\d|HINGE|BAN LE|KHOA|LOCK|LATCH|MS(?:722|303|308|325|406)|AB301|TAI TREO|MOC CAU|EYEBOLT')
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list);report=[]
for r in data['shells']:groups[r['original_dxf']].append(r)
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);prims=[(e,bounds(e)) for e in src.modelspace().query('LINE LWPOLYLINE POLYLINE ARC CIRCLE ELLIPSE SPLINE')];blocks=list(src.modelspace().query('INSERT'))
 for r in rows:
  folder=OUT/'Mau'/r['id'];sheet=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'))['source_sheet_bounds'];chosen=[];hardware=[];faces=[]
  for e in blocks:
   definition=dynblkhelper.get_dynamic_block_definition(e);name=definition.name if definition else e.dxf.name
   if HARDWARE.search(norm(name)) and sheet[0]<=e.dxf.insert.x<=sheet[2] and sheet[1]<=e.dxf.insert.y<=sheet[3]:chosen.append(e);hardware.append({'handle':e.dxf.handle,'name':name})
  for f in r['faces']:
   text=f['source_label'].upper();x,y=f['label_position_clean'];selected=[]
   if any(t in text for t in ('BOTTOM','TOP VIEW','NOC','DAY')):
    w=r.get('dimensions_mm',{}).get('width') or 500;depth=r.get('dimensions_mm',{}).get('depth') or 250
    # Source horizontal views sit immediately above their original labels.
    region=(x-w/2-70,y+12,x+w/2+70,y+depth+260)
    selected=[e for e,b in prims if b and inside(b,region) and e.dxf.layer.lower()!='defpoints']
    chosen.extend(selected)
   faces.append({'label':f['source_label'],'label_handle':f['source_label_handle'],'horizontal_source_entities':[e.dxf.handle for e in selected]})
  changes={}
  for filename in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
   doc=ezdxf.readfile(folder/filename);existing={signature(e) for e in doc.modelspace() if signature(e)};positions={(e.dxf.name,(round(e.dxf.insert.x,4),round(e.dxf.insert.y,4))) for e in doc.modelspace().query('INSERT')};missing=[]
   for e in chosen:
    if e.dxftype()=='INSERT':
     key=(e.dxf.name,(round(e.dxf.insert.x,4),round(e.dxf.insert.y,4)))
     if key in positions:continue
     positions.add(key)
    else:
     key=signature(e)
     if key in existing:continue
     existing.add(key)
    missing.append(e)
   if missing:
    imp=Importer(src,doc);imp.import_entities(missing);imp.finalize();doc.saveas(folder/filename)
   if filename=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
   changes[filename]=len(missing)
  audit={'id':r['id'],'source_hardware':hardware,'faces':faces,'restored':changes,'semantic_cleaning_review_required':True}
  r['source_mechanical_face_audit']=audit;save(folder/'thong_tin.json',r);report.append(audit)
 save(OUT/'catalog.json',data);save(OUT/'kiem_tra_mat_va_ban_le.json',report);print('Hardware and faces',len(report),flush=True)


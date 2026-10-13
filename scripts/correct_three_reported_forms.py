"""Correct reported form interiors and ME41 measuring-device misclassification."""
import ast,json,logging,os
import ezdxf
from ezdxf import dynblkhelper
from extract_project_helpers import ROOT,OUT,save,inside,bounds
tree=ast.parse((ROOT/'BE_AIDE/scripts/restore_complete_e_side_geometry.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[]),'helpers','exec'))
logging.getLogger('ezdxf').setLevel(logging.ERROR)
data=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));ids={'57907522cde7f903-83','9f5252c1bf56526c-F8DC','cf75f63da27941bc-11FCA93','cf75f63da27941bc-108CDD4','142a10f4b2c12273-108CDD4'};report=[]
all_e_side=bool(os.environ.get('FORM_ALL_E_SIDE_ONLY'))
all_plates=bool(os.environ.get('FORM_ALL_PLATE_INTERIORS'))
if all_e_side or all_plates:ids={r['id'] for r in data['shells']}
for r in data['shells']:
 folder=OUT/'Mau'/r['id'];regions=[];dims=r.get('dimensions_mm') or {};depth=dims.get('depth') or 250
 if r['id'] in ids:
  vertical=[f['source_bounds'] for f in r['faces'] if f.get('source_bounds') and f.get('kind') in ('outer_door','inner_door','mounting_plate','side','front','inner_side')]
  if not vertical:continue
  bottom=min(b[1] for b in vertical);top=max(b[3] for b in vertical)
  for f in r['faces']:
   text=f['source_label'].upper();b=f.get('source_bounds')
   if 'E-SIDE' in text and not all_plates:
    if b:regions.append(('internal_side',(b[0]+30,b[1]+100,b[2]-30,b[3]-100),b[3]-b[1]))
    else:
     x=f['label_position_clean'][0];regions.append(('internal_side',(x-depth/2+30,bottom+100,x+depth/2-30,top-100),top-bottom))
   elif not all_e_side and b and f.get('kind') in ('mounting_plate','inner_door'):
    regions.append(('face_interior',(b[0]+25,b[1]+25,b[2]-25,b[3]-25),b[3]-b[1]))
  if not all_e_side and not all_plates and r['id']=='9f5252c1bf56526c-F8DC':regions.append(('bottom_interior',(2261,-34515,3216,-33580),975))
 changes={}
 for fn in ('ban_ve.dxf','ban_ve_co_khung_goc.dxf'):
  doc=ezdxf.readfile(folder/fn);removed=[]
  for e in list(doc.modelspace()):
   reason=None
   if e.dxftype()=='INSERT':
    definition=dynblkhelper.get_dynamic_block_definition(e);name=definition.name if definition else e.dxf.name
    if name.upper().startswith(('ME41','ME40')):reason='ME41 measuring device, previously misclassified as mechanical lock'
    if name.startswith('_Open') and any(inside((e.dxf.insert.x,e.dxf.insert.y,e.dxf.insert.x,e.dxf.insert.y),region) for kind,region,height in regions):reason='internal_dimension_arrow_of_removed_equipment_or_support'
   elif e.dxftype() in ('LINE','LWPOLYLINE','POLYLINE','ARC','CIRCLE','TEXT','MTEXT','SOLID','POINT'):
    b=bounds(e)
    if b:
     for kind,region,height in regions:
      if not inside(b,region):continue
      # Preserve large sheet outlines and long straight sheet-fold lines.
      if e.dxftype() in ('LWPOLYLINE','POLYLINE') and b[3]-b[1]>height*.65:continue
      if e.dxftype()=='LINE' and b[3]-b[1]>height*.65:continue
      if kind=='bottom_interior' and b[2]-b[0]>900 and b[3]-b[1]>500:continue
      reason=kind+'_electrical_or_support_residue';break
   if reason:
    removed.append({'handle':e.dxf.handle,'type':e.dxftype(),'bounds':bounds(e),'reason':reason,'dxf_attributes':{k:str(v) for k,v in e.dxf.all_existing_dxf_attribs().items()}});doc.modelspace().delete_entity(e)
  if removed:
   doc.saveas(folder/fn)
   if fn=='ban_ve_co_khung_goc.dxf':render(doc,folder/'xem_truoc.svg')
  changes[fn]=removed
 if any(changes.values()):report.append({'id':r['id'],'changes':changes})
save(OUT/('kiem_tra_noi_bo_tam_lap_toan_bo.json' if all_plates else 'kiem_tra_noi_bo_E_SIDE_toan_bo.json' if all_e_side else 'kiem_tra_sua_ba_mau_va_ME41.json'),report)
print('Changed',len(report),'forms;',sum(len(r['changes']['ban_ve.dxf']) for r in report),'removed entities')

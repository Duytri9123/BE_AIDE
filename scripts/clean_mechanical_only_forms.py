"""Publish anonymous planar mechanical forms, with separate legacy layout references."""
import json,re,logging
raise SystemExit('Superseded: rebuild_source_shell_style.py preserves source colors/dimensions and removes supports per latest request.')
from collections import defaultdict
import ezdxf
from ezdxf import bbox,dynblkhelper
from ezdxf.disassemble import recursive_decompose
from extract_project_helpers import ROOT,OUT,save,render,inside
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for r in d['shells']:groups[r['original_dxf']].append(r)
HARDWARE=re.compile(r'KHOA|LOCK|LATCH|\bMS(?:722|303|308|325|406)|AB301|\bME ?4[01]|^HL\d|BAN LE|HINGE|TAI TREO|THANH U|DO DOC|DO NGANG|^XA ')
SKIP={'TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','HATCH','LEADER','MULTILEADER','POINT','REGION','BODY','3DSOLID','WIPEOUT'}
report=[]
def box(e):
 try:
  b=bbox.extents([e],fast=True);return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
 except:return None
for path,rows in groups.items():
 source=ezdxf.readfile(ROOT/path);hardware=[]
 for e in source.modelspace().query('INSERT'):
  p=dynblkhelper.get_dynamic_block_definition(e);name=p.name if p else e.dxf.name
  if HARDWARE.search(norm(name)):
   b=box(e)
   if b:hardware.append((e,b,name))
 for row in rows:
  folder=OUT/'Mau'/row['id'];original=ezdxf.readfile(folder/'ban_ve.dxf');offset=row['cleaning'].get('accessory_alignment_translation');analysis=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));sheet=analysis['source_sheet_bounds']
  regions=[]
  for e in original.modelspace().query('LWPOLYLINE'):
   pts=list(e.get_points('xy'));xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
   if e.closed and len(pts)==4 and len(xs)==2 and len(ys)==2:
    r=(min(xs),min(ys),max(xs),max(ys))
    if r[2]-r[0]>=120 and r[3]-r[1]>=100:regions.append(r)
  regions=[r for r in regions if not any(r!=q and inside(r,q) for q in regions)]
  clean=ezdxf.new('R2018');clean.units=4;removed=0;unsupported=0
  for e in recursive_decompose(original.modelspace()):
   if e.dxftype() in SKIP:removed+=1;continue
   b=box(e)
   if not b:unsupported+=1;continue
   # Clear fitted equipment, punched electrical layouts and exploded wiring within faces.
   interior=any(inside(b,(r[0]+15,r[1]+15,r[2]-15,r[3]-15)) and not (b[2]-b[0]>(r[2]-r[0])*.8 and b[3]-b[1]>(r[3]-r[1])*.8) for r in regions)
   if interior:removed+=1;continue
   entity=e.copy()
   try:
    if entity.dxftype()=='LINE':entity.dxf.start=(entity.dxf.start.x,entity.dxf.start.y,0);entity.dxf.end=(entity.dxf.end.x,entity.dxf.end.y,0)
    elif entity.dxftype() in ('CIRCLE','ARC'):entity.dxf.center=(entity.dxf.center.x,entity.dxf.center.y,0);entity.dxf.extrusion=(0,0,1)
    elif entity.dxftype()=='LWPOLYLINE':entity.dxf.elevation=0;entity.dxf.extrusion=(0,0,1)
    clean.modelspace().add_entity(entity)
   except:unsupported+=1
  restored=[]
  if offset:
   dx,dy=offset
   for e,b,name in hardware:
    if not inside(b,sheet):continue
    for part in recursive_decompose([e]):
     if part.dxftype() in SKIP:continue
     try:
      copy=part.copy();copy.translate(dx,dy,0);clean.modelspace().add_entity(copy)
     except:unsupported+=1
    restored.append({'source_handle':e.dxf.handle,'name':name})
  clean.saveas(folder/'ban_ve.dxf')
  dims=row.get('dimensions_mm') or {};size=row.get('size_from_source') or ''
  if all(dims.get(k) for k in ('height','width','depth')):size=' × '.join(f'{dims[k]:g}' for k in ('height','width','depth'))+' mm'
  form=row.get('source_specification',{}).get('FORM','');kind='ngoài trời' if 'ngoài trời' in form.lower() else 'trong nhà' if 'trong nhà' in form.lower() else ''
  row['name']='Vỏ tủ'+(' '+kind if kind else '')+(' · '+size if size else ' · '+row['id']);row['description']=' · '.join(x for x in [row.get('material_from_source'),size] if x)
  # Keep only mechanical specifications in the published form profile.
  row['source_title_attributes']={};row.pop('original_title_frame',None);row.pop('source_file',None)
  row['source_specification']={k:v for k,v in row.get('source_specification',{}).items() if k in ('FORM','SIZE','MATERIAL','ASSEMBLY','PAINTING')}
  row['notes']=['Form cơ khí: bỏ thiết bị/đèn/đồng và nội dung dự án; giữ phần vỏ và phần cứng nguồn nhận diện được.','Tên mới theo loại vỏ và kích thước; bố trí đồng/thiết bị cũ chỉ có trong hồ sơ tham chiếu.','Phần hình học chưa nhận diện cần đối chiếu; không tự chọn trước kiểm tra.']
  row['mechanical_cleaning']={'removed_entities':removed,'unsupported_entities':unsupported,'hardware_restored':restored,'flat_modelspace':True,'source_view_count':len(row.get('faces',[])),'needs_review':not bool(offset) or unsupported>0}
  preview=ezdxf.readfile(folder/'ban_ve.dxf');preview.styles.new('FORM_LABEL',dxfattribs={'font':'arial.ttf'})
  for f in row.get('faces',[]):preview.modelspace().add_text(f['source_label'],dxfattribs={'height':32,'style':'FORM_LABEL','insert':tuple(f['label_position_clean'])})
  # Only preserve the actual source sheet perimeter; omit its customer/logo/title grid.
  if offset:
   dx,dy=offset;x0,y0,x1,y1=sheet
   preview.modelspace().add_lwpolyline([(x0+dx,y0+dy),(x1+dx,y0+dy),(x1+dx,y1+dy),(x0+dx,y1+dy)],close=True)
  preview.saveas(folder/'ban_ve_co_khung_goc.dxf');render(preview,folder/'xem_truoc.svg');save(folder/'thong_tin.json',row)
  assert not list(clean.modelspace().query('INSERT TEXT MTEXT ATTRIB ATTDEF DIMENSION HATCH REGION BODY 3DSOLID'))
  report.append({'id':row['id'],'name':row['name'],**row['mechanical_cleaning']})
 save(OUT/'catalog.json',d);save(OUT/'kiem_tra_form_co_khi.json',report);print(path,'mechanical only',flush=True)
print('Mechanical forms cleaned',len(report))

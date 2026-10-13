"""Source face labels, outer perimeter, lamp removal and separate copper route evidence."""
import json,re,logging
from collections import defaultdict
import ezdxf
from ezdxf import bbox,dynblkhelper
from extract_project_helpers import ROOT,OUT,save,render,inside
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
LABELS=[(r'1ST DOOR|MAT CANH NGOAI|CANH NGOAI','outer_door','Cánh ngoài'),(r'2ND DOOR|MAT CANH TRONG|CANH TRONG','inner_door','Cánh trong'),(r'EQUIPMENT VIEW|BEN TRONG TU|TAM LAP|MAT TRONG TU','mounting_plate','Bên trong tủ'),(r'E-SIDE VIEW','inner_side','Mặt bên trong'),(r'SIDE VIEW|HONG TU|MAT HONG','side','Mặt hông'),(r'TOP VIEW|NOC TU|MAT TREN','top','Mặt trên'),(r'BOTTOM VIEW|DAY TU','bottom','Mặt đáy'),(r'FRONT VIEW|MAT TRUOC','front','Mặt trước'),(r'KHUNG TU|KHUNG NGOAI','frame','Khung ngoài')]
LAMP=re.compile(r'LIGHT|PILOT|DEN BAO|^DEN (DO|VANG|XANH)|^DCHINT')
ELECTRIC=re.compile(r'MCCB|MCB|ACB|RCBO|RCCB|METASOL|CONTACTOR|PLC|ATS|METER|VOLTMET|AMPERE|SELECTOR|BUTTON|FUSE|ISOLATE BKD|SU KEP|THANH DONG|BUSBAR|CAU DAU')
HARDWARE=re.compile(r'MS406|MS722|AB301|KHOA|LOCK|LATCH|BAN LE|HINGE|^HL\d|TAI TREO|KHUNG TU|KHUNG NGOAI|VO TU|CANH|DOOR FRAME')
SKIP={'TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','MULTILEADER','HATCH'}
def b(e):
 try:
  x=bbox.extents([e],fast=True);return (x.extmin.x,x.extmin.y,x.extmax.x,x.extmax.y) if x.has_data else None
 except:return None
def name(e):
 p=dynblkhelper.get_dynamic_block_definition(e);return p.name if p else e.dxf.name
def visible(e):
 if e.dxftype() in SKIP:return
 if e.dxftype()=='INSERT':
  n=norm(name(e))
  if LAMP.search(n) or ELECTRIC.search(n):return
  try:
   for v in e.virtual_entities():yield from visible(v)
  except:return
 elif e.dxftype()=='LINE' and abs(e.dxf.start.x-e.dxf.end.x)>.01 and abs(e.dxf.start.y-e.dxf.end.y)>.01:return
 else:yield e.copy()
def rects(model):
 rs=[]
 for e in model.query('LWPOLYLINE'):
  pts=list(e.get_points('xy'));xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
  if e.closed and len(pts)==4 and len(xs)==2 and len(ys)==2:
   r=(min(xs),min(ys),max(xs),max(ys))
   if 150<=r[2]-r[0]<=3000 and 150<=r[3]-r[1]<=3000:rs.append((r,e))
 return rs
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups=defaultdict(list)
for row in d['shells']:groups[row['original_dxf']].append(row)
report=[]
for path,rows in groups.items():
 src=ezdxf.readfile(ROOT/path);model=src.modelspace();rectangles=rects(model);labels=[];lamps=[];hardware=[];routes=[];cu_notes=[]
 for e in model:
  t=e.dxftype()
  if t in ('TEXT','MTEXT'):
   text=e.dxf.text if t=='TEXT' else e.plain_text();n=norm(text)
   for pattern,kind,title in LABELS:
    if re.search(pattern,n):labels.append((e,kind,title,text));break
   if re.search(r'CU\s*\d|THANH DONG|DONG\s*\d+\s*[X×]|BUSBAR',n):cu_notes.append((e,text))
  elif t=='INSERT':
   n=norm(name(e))
   if LAMP.search(n):
    box=b(e)
    if box:lamps.append((box,e))
   elif HARDWARE.search(n):
    box=b(e)
    if box:hardware.append((box,e))
   elif re.search(r'THANH DONG|BUSBAR|CU\s*\d',n):routes.append(e)
  elif t in ('LINE','LWPOLYLINE'):
   layer=src.layers.get(e.dxf.layer);color=e.dxf.color if e.dxf.color!=256 else layer.dxf.color
   if color in (1,2,3) or re.search(r'BUS|DONG|WIRE|PHASE',norm(e.dxf.layer)):routes.append(e)
 for row in rows:
  folder=OUT/'Mau'/row['id'];analysis=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));sheet=analysis['source_sheet_bounds'];doc=ezdxf.readfile(folder/'ban_ve.dxf')
  offset=row['cleaning'].get('accessory_alignment_translation')
  if not offset:
   sr=[x for x in rectangles if inside(x[0],sheet)];dr=rects(doc.modelspace());matches=[(s,t) for s in sr for t in dr if round(s[0][2]-s[0][0],1)==round(t[0][2]-t[0][0],1) and round(s[0][3]-s[0][1],1)==round(t[0][3]-t[0][1],1)]
   if matches:
    s,t=min(matches,key=lambda pair:(pair[0][0][0],pair[1][0][0]));offset=[t[0][0]-s[0][0],t[0][1]-s[0][1]]
  faces=[];removed=0;restored=0
  if offset:
   dx,dy=offset;shift=lambda r:(r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy)
   for e,kind,title,text in labels:
    pt=e.dxf.insert
    if not (sheet[0]<=pt.x<=sheet[2] and sheet[1]<=pt.y<=sheet[3]):continue
    gap=lambda r:max(r[1]-pt.y,pt.y-r[3],0)
    candidates=[(r,poly) for r,poly in rectangles if inside(r,sheet) and r[0]-100<=pt.x<=r[2]+100 and gap(r)<=500]
    if not candidates:continue
    region,poly=min(candidates,key=lambda v:(gap(v[0]),abs((v[0][0]+v[0][2])/2-pt.x),-(v[0][2]-v[0][0])*(v[0][3]-v[0][1])))
    faces.append({'id':row['id']+'-'+e.dxf.handle,'kind':kind,'name':title,'source_label':text,'source_label_handle':e.dxf.handle,'source_bounds':list(region),'clean_bounds':list(shift(region)),'label_position_clean':[pt.x+dx,pt.y+dy],'identification_basis':'source_face_label','source_perimeter_handle':poly.dxf.handle})
    if kind in ('outer_door','frame'):
     area=shift(region)
     if not any(all(abs(a-z)<.1 for a,z in zip(r,area)) for r,_ in rects(doc.modelspace())):
      copy=poly.copy();copy.translate(dx,dy,0);doc.modelspace().add_entity(copy);restored+=1
     for box,hw in hardware:
      if not inside(box,region):continue
      # Restore hardware only when its source footprint is empty in the clean view.
      target=shift(box)
      if any((eb:=b(x)) and inside(eb,target) for x in doc.modelspace()):continue
      for part in visible(hw):part.translate(dx,dy,0);doc.modelspace().add_entity(part);restored+=1
   source_lamps=[(shift(box),e.dxf.handle) for box,e in lamps if inside(box,sheet)]
   for e in list(doc.modelspace()):
    box=b(e)
    if box is None and e.dxftype()=='INSERT':p=e.dxf.insert;box=(p.x,p.y,p.x,p.y)
    pilot_circle=e.dxftype()=='CIRCLE' and e.dxf.color in (1,2,3) and 7<=e.dxf.radius<=18
    if pilot_circle or (box and any(inside(box,area) for area,_ in source_lamps)):doc.modelspace().delete_entity(e);removed+=1
   doc.saveas(folder/'ban_ve.dxf')
  # Source copper evidence remains independent of the empty form.
  copper=ezdxf.new('R2018');copper.units=4;candidates=[]
  for e in routes:
   box=b(e)
   if not box or not inside(box,sheet):continue
   record={'source_handle':e.dxf.handle,'type':e.dxftype(),'layer':e.dxf.layer,'color':e.dxf.color,'source_bounds':list(box),'material_verified':False,'evidence':'source_busbar_name' if e.dxftype()=='INSERT' else 'colored_or_named_layer_route_candidate'}
   if e.dxftype()=='LINE':record['start_source']=list(e.dxf.start);record['end_source']=list(e.dxf.end);copper.modelspace().add_entity(e.copy())
   elif e.dxftype()=='LWPOLYLINE':record['points_source']=[list(p) for p in e.get_points()];copper.modelspace().add_entity(e.copy())
   else:record['block_name']=name(e)
   candidates.append(record)
  copper.saveas(folder/'tham_chieu_dong_goc.dxf')
  copper_data={'cabinet_id':row['id'],'cabinet_name':row['name'],'source_file':row['source_file'],'coordinate_scope':'original_source_sheet_multiple_views','route_candidates':candidates,'source_notes':[{'source_handle':e.dxf.handle,'text':text,'source_point':list(e.dxf.insert)} for e,text in cu_notes if sheet[0]<=e.dxf.insert.x<=sheet[2] and sheet[1]<=e.dxf.insert.y<=sheet[3]],'layout_occurrences_reference':'bo_tri_goc.json','reference_dxf':'tham_chieu_dong_goc.dxf','verified_material':None,'cross_section_mm2':None,'current_rating_a':None,'must_recheck':['gán đúng mặt và pha','vật liệu/tiết diện theo nguồn','điểm gá và cọc đấu','bán kính uốn và khoảng hở','chịu nhiệt/ngắn mạch'],'reuse_policy':'Giữ cách đi đồng gốc để tham khảo; thay model/cọc đấu hoặc bố trí phải kiểm tra lại. Nét màu không tự chứng minh là đồng.'}
  save(folder/'tham_chieu_dong_goc.json',copper_data)
  analysis['busbar_and_wire_routes']['source_reference_json']='tham_chieu_dong_goc.json';analysis['busbar_and_wire_routes']['source_reference_dxf']='tham_chieu_dong_goc.dxf';analysis['source_faces']=faces;save(folder/'bo_tri_goc.json',analysis)
  row['faces']=faces;row['drawing_labels']=[f['name'] for f in faces];row['copper_reference_json']=f"Mau/{row['id']}/tham_chieu_dong_goc.json";row['cleaning']['lamp_geometry_removed']=removed;row['cleaning']['outer_perimeter_and_hardware_restored']=restored;row['cleaning_policy']['preserve']='tên tủ, loại tôn, kết cấu vỏ, khóa và bản lề; không giữ đèn/đồng trong CAD form'
  # Names belong to the preview; insertion CAD remains free of annotation.
  preview=ezdxf.readfile(folder/'ban_ve.dxf')
  preview.styles.new('AIDE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
  for face in faces:
   area=face['clean_bounds'];preview.modelspace().add_text(face['name'],dxfattribs={'height':32,'style':'AIDE_FACE_LABEL','insert':(area[0],area[1]-65)})
  render(preview,folder/'xem_truoc.svg');save(folder/'thong_tin.json',row)
  report.append({'id':row['id'],'faces':len(faces),'outer_door_identified':any(f['kind']=='outer_door' for f in faces),'outer_restored_entities':restored,'lamps_removed':removed,'copper_reference_candidates':len(candidates),'alignment_verified':bool(offset)})
 save(OUT/'catalog.json',d);save(OUT/'kiem_tra_mat_va_dong.json',report);print(path,'faces and copper reference',flush=True)
print('Updated',len(report),'sheets')

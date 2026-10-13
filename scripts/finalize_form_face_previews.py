import json
import ezdxf
from extract_project_helpers import OUT,save,render
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));analyses=[]
for row in d['shells']:
 folder=OUT/'Mau'/row['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');reference=json.loads((folder/'tham_chieu_dong_goc.json').read_text(encoding='utf-8'));offset=row['cleaning'].get('accessory_alignment_translation');removed=0
 if offset:
  dx,dy=offset;lines=[]
  for r in reference['route_candidates']:
   if r['type']=='LINE':
    a=r['start_source'];b=r['end_source'];lines.append(((a[0]+dx,a[1]+dy),(b[0]+dx,b[1]+dy)))
  def near(a,b):return abs(a[0]-b[0])<.01 and abs(a[1]-b[1])<.01
  for e in list(doc.modelspace().query('LINE')):
   a=e.dxf.start;b=e.dxf.end
   if any((near(a,x) and near(b,y)) or (near(a,y) and near(b,x)) for x,y in lines):doc.modelspace().delete_entity(e);removed+=1
 if removed:doc.saveas(folder/'ban_ve.dxf')
 row['cleaning']['source_route_lines_removed']=removed
 row['face_review']={'outer_door':'identified_from_source_label' if any(f['kind']=='outer_door' for f in row.get('faces',[])) else 'source_label_not_identified_requires_review','multiple_views':True,'unlabelled_views':'chưa nhận diện tên; không tự gán tên/mặt'}
 preview=ezdxf.readfile(folder/'ban_ve.dxf');preview.styles.new('AIDE_FACE_LABEL',dxfattribs={'font':'arial.ttf'})
 for face in row.get('faces',[]):
  r=face['clean_bounds'];preview.modelspace().add_text(face['name'],dxfattribs={'height':32,'style':'AIDE_FACE_LABEL','insert':(r[0],r[1]-65)})
 render(preview,folder/'xem_truoc.svg');save(folder/'thong_tin.json',row)
 a=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));a['reuse_compatibility']['clean_cad_scope']='không có đèn/đồng/thiết bị điện; giữ cơ khí nhận diện được';a['source_faces']=row.get('faces',[]);save(folder/'bo_tri_goc.json',a);analyses.append(a)
 assert not list(doc.modelspace().query('TEXT MTEXT DIMENSION HATCH'))
 assert row['name']==row['source_title_attributes']['DRAWING_NAME']
 assert row['material_from_source']==row['source_specification']['MATERIAL']
save(OUT/'catalog.json',d)
p=OUT/'phan_tich_bo_tri_va_form.json';all_data=json.loads(p.read_text(encoding='utf-8'));all_data['items']=analyses;save(p,all_data)
print('Verified',len(d['shells']),'forms; labelled faces',sum(len(r.get('faces',[])) for r in d['shells']))

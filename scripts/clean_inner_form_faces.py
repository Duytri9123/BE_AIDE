raise SystemExit('Không làm trống mặt cơ khí. Theo yêu cầu mới: chỉ xóa thiết bị điện; giữ khóa, bản lề và kết cấu. Dùng rebuild_tudien_clean_forms.py.')
import json
import ezdxf
from ezdxf import bbox
from extract_project_helpers import OUT,save,render,inside
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'))
for row in d['shells']:
 folder=OUT/'Mau'/row['id'];doc=ezdxf.readfile(folder/'ban_ve.dxf');regions=[]
 for e in doc.modelspace().query('LWPOLYLINE'):
  pts=list(e.get_points('xy'));xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
  if e.closed and len(pts)==4 and len(xs)==2 and len(ys)==2:
   r=(min(xs),min(ys),max(xs),max(ys))
   if 200<=r[2]-r[0]<=3000 and 300<=r[3]-r[1]<=3000:regions.append(r)
 regions=[r for r in regions if not any(r!=q and inside(r,q) for q in regions)]
 outer=[]
 for r in regions:
  # A clustered group of source pilot circles identifies an instrumented outer door.
  lamps=[e for e in doc.modelspace().query('CIRCLE') if 7<=e.dxf.radius<=18 and r[0]<e.dxf.center.x<r[2] and r[1]<e.dxf.center.y<r[3]]
  if any(abs(a.dxf.center.y-b.dxf.center.y)<=3 and 20<=abs(a.dxf.center.x-b.dxf.center.x)<=120 for i,a in enumerate(lamps) for b in lamps[i+1:]):outer.append(r)
 removed=0
 for e in list(doc.modelspace()):
  b=bbox.extents([e],fast=True)
  if not b.has_data:
   if e.dxftype()!='INSERT':continue
   p=e.dxf.insert;eb=(p.x,p.y,p.x,p.y)
  else:eb=(b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y)
  if any(inside(eb,r) for r in outer):continue
  if any(inside(eb,(r[0]+20,r[1]+20,r[2]-20,r[3]-20)) for r in regions):doc.modelspace().delete_entity(e);removed+=1
 if removed:doc.saveas(folder/'ban_ve.dxf');render(doc,folder/'xem_truoc.svg')
 row['cleaning']['inner_face_geometry_removed']=removed
 row['cleaning']['inner_face_review_status']='instrumented_outer_doors_preserved_other_face_interiors_cleared_requires_view_confirmation'
 row['notes'].append('Đã làm trống nội thất các mặt không nhận diện là cánh có cụm đèn; cần xác nhận mặt cánh ngoài không có đèn trước dùng.')
 save(folder/'thong_tin.json',row)
save(OUT/'catalog.json',d)
print('Cleared inner regions:',len(d['shells']))

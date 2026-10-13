"""Audit every profile and independent insertion CAD; do not infer physical identity from paths."""
import json,hashlib
from collections import defaultdict
from pathlib import Path
import ezdxf
from ezdxf import bbox
ROOT=Path(__file__).resolve().parents[1]/'data'/'CatalogTB'
results=[];shared=defaultdict(list)
for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
 d=json.loads(p.read_text(encoding='utf-8'));errors=[];needs=[];faces=[]
 for v in d.get('cad_don',[]):
  q=p.parent/v['duong_dan'];face=v['huong_nhin'];faces.append(face)
  if not q.is_file():errors.append('Thiếu DXF: '+v['id_hinh_goc']);continue
  doc=ezdxf.readfile(q);b=bbox.extents(doc.modelspace(),fast=True)
  if doc.units!=4:errors.append('Đơn vị không phải mm: '+v['id_hinh_goc'])
  if not b.has_data:errors.append('CAD không có hình học: '+v['id_hinh_goc'])
  elif abs(b.center.x)>.02 or abs(b.center.y)>.02:errors.append('CAD chưa đặt tâm: '+v['id_hinh_goc'])
  if any(e.dxf.get('invisible',0) for e in doc.modelspace()):needs.append('Có thành phần ẩn: '+v['id_hinh_goc'])
  if 'Chưa xác định' in face or v.get('bo_tri_trong_tu',{}).get('cho_phep_chen') is False:needs.append('Cần xác nhận mặt: '+v['id_hinh_goc'])
  svg=q.parent/'xem_truoc.svg'
  if not svg.exists():errors.append('Thiếu SVG: '+v['id_hinh_goc'])
  else:shared[hashlib.sha256(svg.read_bytes()).hexdigest()].append({'ho_so':p.parent.relative_to(ROOT).as_posix(),'cad':v['id_hinh_goc']})
 primary=d.get('cad_chen_tu',{})
 if primary.get('id_hinh_goc') not in {v['id_hinh_goc'] for v in d.get('cad_don',[])}:errors.append('Mặt chính không nằm trong hồ sơ')
 if not (p.parent/primary.get('duong_dan','missing')).is_file():errors.append('Thiếu DXF mặt chính')
 results.append({'ho_so':p.parent.relative_to(ROOT).as_posix(),'ten':d['ten_san_pham'],'cac_mat':faces,'mat_chinh':primary.get('huong_nhin'),'mat_con_thieu_da_xac_dinh':d.get('cac_mat_con_thieu',[]),'loi':errors,'can_doi_chieu':sorted(set(needs))})
report={'so_ho_so':len(results),'so_cad':sum(len(r['cac_mat']) for r in results),'so_ho_so_co_loi':sum(bool(r['loi']) for r in results),'so_ho_so_can_doi_chieu':sum(bool(r['can_doi_chieu']) for r in results),'cac_ho_so':results,'cad_dung_chung':[v for v in shared.values() if len({r['ho_so'] for r in v})>1]}
(ROOT/'kiem_tra_toan_bo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('cac_ho_so','cad_dung_chung')},ensure_ascii=False))
for r in results:
 if r['loi']:print(r['ho_so'],r['loi'])

"""Record final selection and resize rules; exclude unresolved boundary sheets."""
import json,re
import ezdxf
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB/Form tủ'
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
d=json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'));accepted=[];excluded=d.get('excluded_shells',[])
for r in d['shells']:
 preview=ezdxf.readfile(ROOT/'Mau'/r['id']/'ban_ve_co_khung_goc.dxf')
 scales=sorted({e.dxf.text.strip() for e in preview.modelspace().query('TEXT') if re.fullmatch(r'\d+(?:\.\d+)?:\d+(?:\.\d+)?',e.dxf.text.strip())})
 specs=[{a.dxf.tag:a.dxf.text for a in e.attribs} for e in preview.modelspace().query('INSERT') if any(a.dxf.tag=='MATERIAL' for a in e.attribs)]
 standards=[e.dxf.name for e in preview.modelspace().query('INSERT') if 'STANDARD' in e.dxf.name.upper()]
 r['technical_source_parameters']={'technical_tables':specs,'drawing_scale':scales[0] if len(scales)==1 else None,'scale_candidates':scales,'standard_drawing_symbols':standards,'standard_basis':'drawing symbol; does not establish electrical enclosure certification'}
 assert specs, 'Missing original technical table: '+r['id']
 r['resize_policy']={'coordinate_system':'original_source_modelspace','preserve_features':['source_colors','locks','hinges','lifting_hooks','mounting_tabs','ventilation','mechanical_fastener_holes','material','paint','standard'],'update_on_size_change':['shell_geometry','dimension_annotations','SIZE','dimensions_mm'],'update_scale_only_on_drawing_scale_change':True,'never_uniformly_scale_hardware_or_hole_diameters':True,'drawing_name_cell':'blank','requires_design_review':True}
 r['blank_source_frame']['content_removed']=['drawing_name_value','customer_value','company','logo','dates']
 r['blank_source_frame']['retained']=['grid_geometry','field_labels','STANDARD','SCALE','sheet_grid_indices','technical_specifications']
 r['auto_select']=False
 if r['mechanical_cleaning']['source_regions']==0:
  r['status']='excluded_pending_source_boundary_review';excluded.append(r)
 else:accepted.append(r)
 save(ROOT/'Mau'/r['id']/'thong_tin.json',r)
d['shells']=accepted;d['excluded_shells']=excluded
d['rules']=['CAD nguồn Tudien giữ nguyên.','Form sạch giữ vỏ, khóa, bản lề; bỏ thiết bị, lỗ thiết bị, đèn, đồng và đố.','SIDE VIEW giữ thông gió, móc, tai và lỗ cơ khí nguồn.','Khung tên giữ nhãn và Standard/Scale; ô tên, khách hàng, công ty và ngày tháng để trống.','Giữ bảng kỹ thuật và màu nguồn. Chỉ đổi kích thước/Scale khi hình học/tỷ lệ thực sự thay đổi.','Bố trí thiết bị/đồng gốc lưu riêng; không nhập vào form.','Không tự chọn các vùng chưa kiểm chứng.']
save(ROOT/'catalog.json',d);save(ROOT/'form_can_doi_chieu_duong_bao.json',excluded)
print('Published candidates',len(accepted),'excluded boundary review',len(excluded))

import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
p=ROOT/'Form tủ/catalog.json';data=json.loads(p.read_text(encoding='utf-8'))
for r in data['shells']:
 r['drawing_labels']=[f.get('display_label',f['source_label']) for f in r.get('faces',[])];r['description']=' · '.join(x for x in [r.get('material_from_source'),r.get('size_from_source')] if x)
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
tree=ast.parse(Path(__file__).with_name('build_catalogtb_cabinet_forms.py').read_text(encoding='utf-8'))
page=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='page' for t in n.targets))
page=page.replace('Mẫu bố trí đã lọc · kích thước theo thứ tự <b>Cao × Rộng × Sâu (mm)</b>.','Mẫu bố trí từ dự án · CAD dự án đã làm sạch · giữ tên tủ và loại tôn gốc.').replace('Đã loại các bản khai triển và chi tiết gia công khỏi danh sách chính. Bản CAD nguồn có nhiều mặt trên cùng tờ. Xem và chọn mặt cần thiết trước khi bố trí.','Đã bỏ chữ, kích thước, hatch và nét gạch chéo; giữ cơ khí, khóa và đèn đã nhận diện. CAD còn nhiều mặt trên một tờ; cần đối chiếu trước khi chèn.').replace('<option value="indoor">Trong nhà</option><option value="outdoor">Ngoài trời</option>','<option value="project">Mẫu dự án</option>').replace('Form phân khoang: chưa xác nhận','Mặt tủ / chiều sâu: cần xác nhận').replace('Tải bản CAD nguồn','Tải CAD mẫu đã làm sạch')
page=page.replace('<small>Mặt tủ / chiều sâu: cần xác nhận</small>', '<small>Form phân khoang: ${r.separation_review?.declared_form ? "Nguồn ghi Form "+e(r.separation_review.declared_form)+" · chưa kiểm chứng" : "Chưa đủ bằng chứng xác định"}</small>${r.layout_analysis_json ? `<a href="${e(r.layout_analysis_json)}">JSON bố trí gốc và đánh giá Form</a>` : ""}')
page=page.replace('JSON danh mục</a>','JSON danh mục</a> · <a href="phan_tich_bo_tri_va_form.json">Phân tích bố trí và 7 Form</a> · <a href="kiem_tra_nguon.json">Báo cáo nguồn</a>')
page=page.replace('Báo cáo nguồn</a>','Báo cáo nguồn</a> · <a href="kiem_tra_e_side_view.json">Kiểm tra E-SIDE VIEW</a>')
page=page.replace('Kiểm tra E-SIDE VIEW</a>','Kiểm tra E-SIDE VIEW</a> · <a href="kiem_tra_day_du_net_e_side.json">Đối chiếu đầy đủ nét nguồn</a>')
page=page.replace('giữ cơ khí, khóa và đèn đã nhận diện','giữ cơ khí và khóa; đã bỏ đèn và đồng').replace('img{width:100%;height:210px;object-fit:contain;cursor:zoom-in}','img{width:100%;height:280px;object-fit:contain;cursor:zoom-in;border:1px solid #cbd8e3;box-sizing:border-box}')
page=page.replace('Tải CAD mẫu đã làm sạch</a>', 'Tải CAD mẫu đã làm sạch</a>${r.original_title_frame?.preview_cad ? `<br><a href="${e(r.original_title_frame.preview_cad)}" download>Tải CAD có khung tên gốc</a>` : ""}')
page=page.replace('<small>${e(r.drawing_labels.join(\' · \'))}</small>', '<small>${e(r.drawing_labels.join(\' · \'))}</small>${r.copper_reference_json ? `<a href="${e(r.copper_reference_json)}">JSON cách bố trí đồng gốc</a><br>` : ""}')
page=page.replace('Mẫu bố trí từ dự án · CAD dự án đã làm sạch · giữ tên tủ và loại tôn gốc.','Form vỏ tủ cơ khí · tên theo kích thước Cao × Rộng × Sâu (mm).').replace('Đã bỏ chữ, kích thước, hatch và nét gạch chéo; giữ cơ khí và khóa; đã bỏ đèn và đồng. CAD còn nhiều mặt trên một tờ; cần đối chiếu trước khi chèn.','Giữ các mặt vỏ, khóa và bản lề đã nhận diện. Bỏ thiết bị, đèn, đồng và nội dung khách hàng/dự án. Hồ sơ bố trí cũ được lưu riêng để tham khảo; cần kiểm tra cơ khí trước khi sử dụng.')
page=page.replace('Giữ các mặt vỏ, khóa và bản lề đã nhận diện. Bỏ thiết bị, đèn, đồng và nội dung khách hàng/dự án.','Giữ các mặt vỏ, khóa, bản lề, màu nét và kích thước gốc. Bỏ thiết bị, lỗ thiết bị, đèn, đồng, đố và nội dung khách hàng/dự án.')
page=page.replace('r.original_title_frame?.preview_cad','r.blank_source_frame?.preview_cad').replace('r.original_title_frame.preview_cad','r.blank_source_frame.preview_cad').replace('Tải CAD có khung tên gốc','Tải CAD có khung gốc đã xóa nội dung')
page=page.replace('Bỏ thiết bị, lỗ thiết bị, đèn, đồng, đố và nội dung khách hàng/dự án.','Bỏ thiết bị, lỗ thiết bị, đèn, đồng, đố và nội dung khách hàng/dự án. Giữ SIDE VIEW, khung bản vẽ gốc đã xóa nội dung và khe thông gió nguồn đã nhận diện.')
page=page.replace('src="${r.preview}"','src="${r.preview}?v=source-shell-final-21"')
page=page.replace('Hồ sơ bố trí cũ được lưu riêng để tham khảo; cần kiểm tra cơ khí trước khi sử dụng.','Mỗi form giữ bảng thông số kỹ thuật gốc và Standard/Scale. Ô tên bản vẽ để trống. Hồ sơ bố trí cũ được lưu riêng để tham khảo; cần kiểm tra cơ khí trước khi sử dụng.')
page=page.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</',r'<\/')).replace('__REF__','https://cache.industry.siemens.com/dl/files/936/107113936/att_1342112/v1/TIP_Planning_manual_SIVACON_S8_2025-02_EN.pdf')
(ROOT/'Form tủ/index.html').write_text(page,encoding='utf-8')
print('Published',len(data['shells']),'clean source sheets')


# Hoàn thiện thư viện LS — 2026-10-20

Phạm vi đợt này chỉ LS. Không xóa hoặc phân loại lại CAD của hãng khác.

## Kết quả
- Gỡ 11 mặt LS mang nhãn chưa xác định khỏi hồ sơ đang hiển thị và SQLite; hồ sơ không còn mặt được ẩn. API tải theo các hồ sơ này không còn trả bản vẽ.
- Tải thêm 10 DWG chính thức LS (MCCB Metasol và contactor MC). Chuyển DXF bằng AutoCAD Core Console, lưu URL nguồn, metadata và SHA256.
- Tách và xác minh 28 mặt trước/bên cho 14 cấu hình: Metasol cỡ thân 100, 125, 250, 400 với số cực có trong bản vẽ nguồn; contactor MC-6a/9a/12a/18a, MC-32a/40a, MC-50a/65a và MC-75a/85a/100a cuộn AC.
- Các bản vẽ cỡ lớn còn cần đối chiếu không được nhập thành mặt độc lập. Không tự dựng hình 2P/4P hay áp dòng cắt chỉ từ đường bao.
- Thư viện hiển thị: 141 hồ sơ LS, 309 mặt CAD, không còn nhãn/mặt chưa xác định.
- Làm sạch trường thông số trống, cập nhật tên có hãng/loại/họ/số cực, và Icu theo bảng giá khi có dữ liệu. Một thân CAD có thể liên kết nhiều cấu hình điện; không đánh dấu các lựa chọn là CAD đúng SKU đã xác nhận.
- 200 liên kết cấu hình với 155 dòng giá riêng biệt. Bảng giá có 517 dòng LS; không tuyên bố mọi dòng đã có CAD chính xác.
- Bổ sung thông tin số cực/loại cuộn hút cho 322 dòng bảng giá từ chính tiêu đề nhóm hoặc mã có ghi số cực. Giá và các ô nguồn giữ nguyên. Chi tiết: explicit-pricebook-metadata.json.

## Hành vi chọn thiết bị
- Thiết bị chính và phụ kiện phụ thuộc giữ hãng yêu cầu; thiếu CAD LS không tự đổi sang hãng khác.
- Thiết bị phụ không mang hãng riêng được gợi ý qua các hãng, xếp giá dương tăng dần sau lọc thông số.
- Đọc số cực/In/kA viết trong mô tả ngay cả khi trường tách riêng bị bỏ trống. Loại dòng giá không đạt yêu cầu kA hoặc thiếu dữ liệu cần đối chiếu.
- Phân biệt VAC/VDC khi lọc giá. CAD contactor 3P cuộn AC không được ghép giá cuộn DC hoặc bản 4P.
- Các lựa chọn cấu hình vẫn cần đối chiếu Icu/Ics tại điện áp sử dụng, In, kiểu lắp, đầu nối và phụ kiện. Không tự xác nhận mức cắt hay mã mua hàng từ hình CAD.

## UI và triển khai
- Thư viện không có liên kết Xem tài liệu; không hiện mục sản phẩm trống.
- FE bổ sung lọc các giá trị N/A, none, dấu gạch và nhãn chưa có thông tin/chưa cập nhật; ô thiếu dữ liệu để trống.
- FE commit c89bc530 đã push main. Vercel báo triển khai thành công; đã đọc bundle EquipmentLibraryPage đang phục vụ tại https://www.elquote.top và xác nhận có bộ lọc mới.
- API đã nạp lại từng worker khi không có job thiết kế đang chạy, health OK.

## Xác minh
- 41 unittest đạt: ưu tiên hãng, khả năng cắt, VAC/VDC, loại cuộn hút/số cực, tỷ số CT, ghép bao hình, tìm kiếm và quyền xem/tải.
- 28 DXF audit không lỗi, đơn vị mm, SHA256 khớp, không chứa chú thích/kích thước nguồn.
- 56 đường dẫn xem trước/tải của mặt mới đọc được; 14 cặp mặt trước/bên xác định được bao hình.
- Cả 14 hồ sơ CAD mới trả được cấu hình có giá. Kiểm tra riêng contactor chỉ có lựa chọn 3P cuộn AC.
- FE build thành công và prerender 121 trang công khai.

## Nguồn đã kiểm tra
- LS Download Center: https://www.ls-electric.com/ko/download/
- Metasol MCCB CAD: https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id=417152
- Metasol MC CAD: file_list d_id 420008, 420010, 420011, 420012 tại cùng API LS.
- Metasol thông số: https://www.ls-electric.com/upload/customer/download/1526/160715_Metasol_MCCB_E.pdf
- LS Product Finder: https://pfinder.ls-electric.com/IEC/product/mccb_susol.do
- LS America: https://www.lselectricamerica.com/panel-control-technical-data/
- Nguồn đối chiếu CAD khác: https://lselectric-ru.com/equipment/oborudovanie-nizkogo-napryazheniya/

Bằng chứng mặt mới: ../ls-main-faces-2026-10-20.json và ../ls-main-faces-2026-10-20.png. Báo cáo cấu hình: price-configurations.json. Hồ sơ mặt đã gỡ: removed-views.json.

Quy trình tái tạo nằm trong scripts/download_ls_main_cad.py, import_ls_main_faces.py, remove_unresolved_ls_faces.py, enrich_ls_explicit_price_metadata.py và refresh_ls_price_configurations.py. Dữ liệu CAD lớn nằm trong CatalogTB trên máy chủ; việc push FE không tự mang theo các file này.

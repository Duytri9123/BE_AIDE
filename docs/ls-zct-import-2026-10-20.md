# Biến dòng LS — mặt CAD gốc, 2026-10-20

Đã tải CAD trực tiếp từ LS Download Center qua API công khai của trang:
- https://www.ls-electric.com/ko/download/?k_word=ZCT
- https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id=417383
- https://www.ls-electric.com/ko/api/download.ashx?t=file_list&d_id=417380

Nguồn đã lưu (DWG, DXF chuyển đổi bằng AutoCAD Core Console, SHA256 và metadata):
- 45886: Metasol EMPR ZCT_LZT030~080.dwg
- 45887: Metasol EMPR ZCT_LZR030~080(V).dwg
- 45882: 3CT, bản vẽ ghi KBD-21, KBD-22, KBD-42/43, KBD-62/63. Chưa đưa vào nhóm LS vì nguồn tải LS không đủ để xác nhận nhà sản xuất của cụm phụ kiện KBD.

Đối chiếu bổ sung:
- LS Electric: https://www.ls-electric.com/upload/customer/download/1450/MC.pdf
- LS Electric America: https://www.lselectricamerica.com/wp-content/uploads/2024/04/EMPR_EN_C15032-05.pdf
- 2SK: https://2sk.co.kr/emproption

Đã xuất và đưa vào chỉ mục 12 hình cho 4 hồ sơ:
- LZT-030: 3 hình nguồn.
- LZT-050/065/080: 3 hình sơ đồ họ thiết bị, không phải 3 bộ CAD đúng kích thước từng mã. Ví dụ cửa sổ hình nguồn là 70mm, khác ba giá trị trong bảng; không được co giãn thành từng mã.
- LZR-030/050/065(V): 3 hình sơ đồ họ thiết bị, chưa phân bổ mã cụ thể.
- LZR-080(V): 3 hình nguồn.

Tên mặt: mặt xuyên dây, mặt bên, mặt đế gá theo bản vẽ. Không tự suy đoán thêm mặt sau, mặt trên hay hình trục đo. Giữ auto_select=false, needs_review=true và cho_phep_chen=false, do còn cần đối chiếu kích thước nguồn với bảng và đúng phiên bản đặt hàng. Không coi ZCT là CT đo lường thứ cấp 1A/5A. Không suy ra tỷ số từ tên 030/080: đó là cỡ cửa sổ.

Các profile có alias từng mã để tìm kiếm ra đúng nhóm sơ đồ. Nhãn REFERENCE chỉ dùng cho định danh nội bộ; giao diện ghi Sơ đồ họ thiết bị.

Quy trình tái tạo:
1. venv/Scripts/python.exe scripts/download_ls_ct_sources.py
2. venv/Scripts/python.exe scripts/import_ls_ct_faces.py
3. venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'scripts'); from publish_abb_ct_index import main; from import_ls_ct_faces import SPECS; main([x[0] for x in SPECS],'ls-zct-faces-2026-10-20','LS','ZCT')"

Bằng chứng từng hình: ls-zct-faces-2026-10-20.json. Ảnh kiểm tra: ls-zct-faces-2026-10-20.png.

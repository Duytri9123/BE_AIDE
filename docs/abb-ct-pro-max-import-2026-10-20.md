# ABB CT PRO XT / CT MAX — bổ sung mặt CAD 2026-10-20

Đã nhập 12 hình nguồn: mỗi họ có mặt xuyên dây, bên phải, bên trái, trên, dưới và hình trục đo. Tổng đợt biến dòng ABB: 60 hình / 14 họ (48 hình CT1M trước đó).

Nguồn DXF chính thức:
- CT PRO XT: https://search.abb.com/library/Download.aspx?DocumentID=9AKK106930A5222&LanguageCode=en&DocumentPartId=&Action=Launch
- CT MAX: https://search.abb.com/library/Download.aspx?DocumentID=9AKK106930A5223&LanguageCode=en&DocumentPartId=&Action=Launch

Nguồn đối chiếu nhận diện họ thiết bị:
- ABB: https://new.abb.com/low-voltage/cs/nizke-napeti/produkty/modularni-pristroje/merici-pristroje/proudove-transformatory
- Tài liệu ABB được TME lưu: https://www.tme.eu/Document/ded62ee70328f721433e64e3ca89ccd9/ANR96.pdf
- Tài liệu ABB được Farnell lưu: https://www.farnell.com/datasheets/2040200.pdf

Hình học chỉ lấy từ các block chiếu gốc BLOCK10–15 trong DXF ABB. Không dựng thêm mặt bằng phép lật. Khung tên nguồn ghi mm, 1:1; DXF con khai báo INSUNITS=4. Không suy ra tỷ số, VA, cấp chính xác hoặc mã đặt hàng từ hình học. Giữ auto_select=false, needs_review=true; hình trục đo không dùng chèn bố trí.

Kiểm tra: 12 DXF audit không lỗi, đơn vị mm, SHA256, số entity, loại bỏ chú thích/kích thước; 24 đường dẫn preview/DXF qua bộ phân giải API đọc thành công. Tìm kiếm CT PRO XT và CT MAX trả về đúng từng hồ sơ với đủ 6 mặt. Chỉ cập nhật đúng hai hồ sơ SQLite, không dựng lại toàn bộ catalog.

Tái tạo từ nguồn đã lưu:
1. venv/Scripts/python.exe scripts/import_abb_ct_pro_max.py
2. venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'scripts'); from publish_abb_ct_index import main; main(['CT-PRO-XT','CT-MAX'],'abb-ct-pro-max-faces-2026-10-20')"

Chi tiết bằng chứng từng mặt: abb-ct-pro-max-faces-2026-10-20.json. Ảnh kiểm tra: abb-ct-pro-max-faces-2026-10-20.png.

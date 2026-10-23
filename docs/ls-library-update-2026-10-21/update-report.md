# Cập nhật thư viện LS và tìm nguồn CHINT — 21/10/2026

FE commit: 5bf77c94. Vercel triển khai thành công; đã kiểm tra bundle trên https://www.elquote.top có nhãn ngắn FRONT, REAR, SIDE-L, SIDE, TOP, BOTTOM. Các mặt phụ có nhãn ngắn riêng, không lặp hãng/mã thiết bị.

## LS

Bổ sung 8 mẫu tay xoay DH100/DH125/DH250, N-70/N-80, EH100/EH125/EH250: 48 mặt CAD, liên kết 8 dòng giá. Bộ EH được tách khỏi thân MCCB theo tên cụm STEP chính hãng; đã đối chiếu tọa độ và thể tích trước khi tách. Giữ nguyên chiều dài trục mô hình, cần chọn theo tủ thực tế.

Độ phủ hiện tại: 336/517 dòng giá có bộ CAD họ đủ 6 mặt; 43 dòng có CAD còn thiếu mặt; 138 dòng chưa có CAD xác minh. Thư viện LS hiển thị 262 hồ sơ, 997 mặt. Không có DXF bị thiếu hoặc nhãn chưa xác định trong kiểm tra LS.

CAD họ không xác nhận SKU mua hàng; vẫn phải kiểm tra dòng định mức, Icu/Ics và điện áp, số cực, kiểu lắp, cuộn hút, đầu nối, phụ kiện. Không gán các mẫu MC đời cũ có sai khác kích thước hoặc khối UA-4 vào các mã đang thiếu.

Danh sách yêu cầu bổ sung: [JSON](cad-supplement-queue.json). Đối chiếu đầy đủ: [CSV](pricebook-cad-coverage.csv).

## CHINT

Tìm được 219 liên kết CAD chính hãng: NXM 78, NM8N 141. Đây là số liên kết STEP/DWG, bao gồm phụ kiện và biến thể, không phải 219 mẫu đã dùng được. Đã tải 12 STEP.

Nhập 4 mẫu đã kiểm tra: NXM-160S 2P/3P/4P và NXM-250S 3P; tổng 24 mặt, tham chiếu 7 dòng giá. Đối chiếu catalogue NXM trang PDF 9 (mã) và 27 (kích thước). Giữ nguyên tư thế tay gạt nên chiều sâu toàn mô hình khác chiều sâu thân danh nghĩa. Với 4P phải kiểm tra cơ cấu cực N.

8 STEP khác được giữ ở nguồn chờ: NXM-125S có chi tiết nhô làm chiều cao toàn mô hình khác thân; NXM-250S 2P có cụm bên trong ghi 320 và chi tiết rời; NM8N cần kiểm tra tư thế/đầu nối/bao hình. Chưa gán các mẫu này vào giá.

Nguồn: [NXM](https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nxm.html), [NM8N](https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nm8n.html). Danh mục nguồn: [CSV](../chint-research-2026-10-21/official-cad-inventory.csv).

## Kiểm tra

72 mặt mới: đơn vị mm, audit DXF, hình học, không chứa chữ/kích thước chú thích, SHA256, bao hình và SVG; đủ 6 mặt/cùng biến thể, một mặt bên xác nhận chiều sâu. 39 bài kiểm tra liên quan đã đạt.

Chi tiết: [delta-validation.json](delta-validation.json), [service-and-envelope-validation.json](service-and-envelope-validation.json).

# Bổ sung GIMAC EX/M485 ngày 26/10/2026

Đã xử lý thêm một gap: `GIMAC-1000 EX,M485,5A,50Hz,AC/DC100~240V`, bổ sung sáu hình chiếu native và liên kết riêng ID dòng giá. Không mở rộng liên kết theo tiền tố GIMAC.

Lý do loại trước đây cần sửa: NO/EX là cấp chức năng, độc lập với giao tiếp M485/ETH. Catalogue chính hãng trang 14 có bảng mã và hình kích thước chung NOCOMM/M485, riêng Ethernet; trang 5 xác nhận các lựa chọn 5A, 50Hz và AC/DC100–240V. Bản DWG 55455 cung cấp sáu mặt của M485. Đây là liên kết hình học dùng chung được chứng minh bằng catalogue, không phải xác nhận tính năng điện từ hình CAD.

- [Catalogue hãng đã lưu](manufacturer-catalog.pdf), [trang kích thước và bảng mã](dimensions-ordering-page14.png).
- [Hồ sơ, nguồn và ID giá](additions.json), [sáu DXF được kiểm tra](validation.json), [thay đổi độ phủ](coverage-changes.json).
- DXF đơn vị mm, audit không lỗi hoặc sửa tự động. 60 kiểm tra hồi quy đạt.

Kết quả toàn bộ 517 dòng: **373 có CAD, 348 đủ sáu mặt, 25 thiếu mặt, 144 chưa có CAD phù hợp**. Còn **169 gap**, được giữ trong hàng đợi và bảng xử lý từng dòng. Thư viện LS có **242 hồ sơ / 1.128 mặt**.

Đã cập nhật chỉ mục phục vụ tệp và thay lần lượt tám worker của bốn supervisor API hiện có tại `http://127.0.0.1:8000`; tất cả khởi tạo và health 200. Kết quả HTTP có xác thực và hash tải nguồn được ghi trong báo cáo triển khai. Chưa xác nhận tên miền công khai bên ngoài.

Hai contactor MC-6a DC và MC-150a DC vẫn là gap: các cửa sổ hình học đã được rà lại nhưng cần xác minh thêm cấu hình tiếp điểm tương ứng; không dùng hình lỗ gá thay cho mặt sau hoàn chỉnh.

Kiểm tra HTTP cuối cùng đạt: 26 dòng giá, 72/72 DXF tải nguồn khớp hash, hai preview và ba DXF nhóm. Health 4/4 trả 200. Lượt chạy lại giới hạn một luồng OpenBLAS/OMP sau lỗi tài nguyên tạm thời. [Kết quả triển khai](deployment-result.json), [log HTTP](../ls-all-cad-2026-10-24/live-api-targeted-final-20261026.json).


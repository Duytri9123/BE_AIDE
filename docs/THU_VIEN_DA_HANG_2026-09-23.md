# Cập nhật thư viện thiết bị trong dự án — 23/09/2026

## Giao diện
- Nút Thiết bị hệ thống & phụ kiện mở cửa sổ thư viện lớn ngay trong dự án, dùng chung danh mục với trang quản lý.
- Chọn nhanh đồng hồ, đèn, bản lề, khóa, cầu đấu, thanh đồng. Tên thiết bị ở cả hai chế độ bảng dự án mở tra cứu theo mã hàng hoặc nhóm.
- Tab CAD có danh sách bên trái, preview lớn bên phải, tìm kiếm, lọc hãng và tải DXF.
- Linh kiện liên kết CAD mở hình học block gốc. Các thiết bị chỉ có kích thước dùng hình bao được ghi nhãn; đèn có đường kính ngoài dùng hình tròn, không suy đoán chiều sâu.
- Ẩn mục thông số điện và kích thước trống cho linh kiện cơ khí.

## Nguồn và kết quả
- Dùng ba DWG mới nhất do người dùng cung cấp; BAK lưu thông tin đối chiếu, không nhập trùng. SHA256 và kích thước file trong data/device_layouts/source_inventory.json.
- CHINT: 75 block hợp lệ; Schneider: 245 hợp lệ, 3 loại; tổng hợp: 319 hợp lệ. Tổng thêm 639, cùng LS có 788 block sử dụng.
- 67 mục linh kiện nhận diện bằng tên block được đưa vào catalog; tổng DB 1.687 mục. Chưa có đơn giá, model và hướng nhìn được xác minh nên không tự gán thông số mua sắm.
- CHINT khai báo inch, Schneider không khai báo đơn vị, tổng hợp khai báo mm. Giữ nguyên tọa độ và đơn vị; không lấy bao hình 2D làm kích thước sản phẩm.
- File CHINT chứa cả LS/Hyundai. Hãng theo tên block/quy tắc dòng nhận diện, không mặc định toàn bộ theo tên file. Phụ kiện không có bằng chứng giữ Chưa xác định hãng.
- Block hỏng Schneider: dfhfeher, fghd (DXF audit cần sửa); ®ssf®ff (không có bao 2D hợp lệ). Không đưa các file này vào bản phát hành.

## Kiểm tra
- 34 kiểm thử backend đạt, gồm phân hãng hỗn hợp, phân nhóm linh kiện, bảo toàn đơn vị, preview SVG bản lề và đường kính đèn.
- Frontend production build thành công; kiểm tra trình duyệt cục bộ bằng fixture đọc từ DB và API: modal thư viện và hình CAD bản lề hiển thị được. Đây không phải kiểm thử website công khai.
- SQLite sao lưu tại tmp/catalog_backup_multibrand_20260923.db trước cập nhật. Không đưa DB vào Git.
- Cần khởi động lại dịch vụ backend để nạp mã mới; lần tự động thực hiện trong phiên này bị bộ kiểm duyệt công cụ từ chối (blocked by policy).

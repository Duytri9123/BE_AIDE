# Cập nhật thư viện từ hai file catalog người dùng cung cấp

Nguồn: `E:/Downloads/catalog_data.json` và `E:/Downloads/catalog_accessories.json`.

## Kết quả đối chiếu

- Hai file nguồn giống nội dung JSON hiện có trong backend tại thời điểm kiểm tra. Không có bản ghi thiết bị mới hơn để thay thế.
- Trang Thư viện đọc bảng `device_models` trong cơ sở dữ liệu, trong khi AI đọc JSON. Bảng này có 0 model trước đồng bộ, gây trang trống dù tiêu đề ghi cứng “1.498+”.
- Đã đồng bộ 1.498 thiết bị và 122 mục phụ kiện: 84 thanh đồng, 25 phụ kiện cơ khí, 13 phụ kiện mặt cánh; tổng 1.620 mục. Không trùng SKU; phụ kiện dùng tiền tố `ACC:` để phân biệt.
- Nhãn số lượng nhóm phụ kiện cơ khí ghi 19 nhưng thực tế có 25: đã sửa `badge` theo chiều dài danh sách, không bỏ sáu mục dư.
- 1.418/1.498 thiết bị có `_verified=false`; giữ trạng thái chưa xác minh. 80 bản ghi được nguồn đánh dấu đã xác minh không đồng nghĩa lượt kiểm tra này đã chứng thực thông số nhà sản xuất.
- 18 thiết bị chưa có giá: giữ cờ `price_available=false`, không tự điền giá. Cột DB dùng 0 theo cấu trúc hiện tại; giao diện hiển thị liên hệ thay vì coi là miễn phí.
- 1.498 thiết bị có đủ trường kích thước W/H/D; chưa đối chiếu trị số với datasheet nhà sản xuất. Dòng chịu tải thanh đồng trong phụ kiện là giá trị từ nguồn, chưa phải xác nhận khả năng mang tải trong mọi điều kiện lắp đặt.
- Phụ kiện không có hãng được ghi “Chưa xác định hãng”; không tự gán LS.

## Thay đổi trên trang

- Tổng số mục lấy từ dữ liệu đã tải, không ghi cứng 1.498.
- Thay bộ lọc/từ khóa sẽ quay về trang đầu, tránh hiển thị rỗng do đang ở trang cuối.
- Chi tiết thiết bị hiển thị trạng thái xác minh thông số.
- Chi tiết LS có phần CAD: tìm/chọn hình trong thư viện, xem ảnh vector sinh từ DXF, thu phóng và tải DXF.
- CAD hiện là hình tham khảo được người dùng chọn. Chưa có mapping đã xác minh model→mặt trước/bên/trên; không tự gán hình gần giống hoặc tạo mặt thiếu.

## Kiểm chứng và khôi phục

- API đang chạy tại localhost:8000 trả đủ 1.620 mục, trong đó 122 SKU phụ kiện.
- Backend sinh được SVG của `LS 800AF 3P`; kiểm thử SVG hợp lệ và từ chối ID không có trong manifest.
- Frontend production build thành công. Chưa kiểm tra thao tác trên trình duyệt website công khai.
- Đã sao lưu SQLite bằng cơ chế SQLite backup, cùng hai JSON cũ, tại `tmp/catalog_backup_20260923_132010/` trước đồng bộ.
- File nguồn trong Downloads không bị sửa. Script `scripts/seed_devices_catalog.py` cập nhật/thêm theo SKU trong transaction; không xóa dữ liệu khác và không đặt lại chiết khấu của model đã tồn tại.

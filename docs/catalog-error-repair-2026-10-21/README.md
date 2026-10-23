# Đã xử lý lỗi và cập nhật thư viện

- Cách ly hai mặt ABB `A02_abb-V002`, `A02_abb-V003` khỏi hồ sơ ZCT-300A. Tệp được chuyển khỏi thư mục CAD sử dụng sang bản lưu trong báo cáo; không tự gán chúng thành các mặt của vòng ZCT. Cập nhật cả hồ sơ nguồn, danh sách CAD trong SQLite và chỉ mục hiển thị.
- Chặn hai mặt này cả bằng ID gốc và ID công khai; các đường dẫn xem trước/tải cũ trả 404. Dữ liệu hiển thị còn lưu trong bộ nhớ cũng được lọc.
- Làm sạch 18 DXF có lỗi tham chiếu DICTIONARY/MLEADERSTYLE. Sau khi lưu, đọc và audit lại không còn lỗi hoặc sửa chữa phát sinh. So sánh đầy đủ tag thực thể của modelspace và các block với bản sao trước sửa: không thay đổi hình học.
- Cập nhật hash kiểm chứng cho các tệp dẫn xuất đã làm sạch, giữ bản nguồn và hồ sơ trước sửa. Không đổi hash tài liệu hãng hoặc DWG gốc.
- Bộ tạo chỉ mục và danh mục chèn CAD chặn mặt chưa xác định, tệp thiếu, hình rỗng, đơn vị chưa xác minh, DXF còn lỗi/sửa chữa audit, SVG không đọc được và hình có trạng thái lỗi hình học chưa giải quyết.
- Kiểm tra hash DXF/ảnh xem trước đã được kiểm chứng khi hiển thị dữ liệu cũ và khi tải tệp. Nếu nội dung thay đổi so với bản đã kiểm chứng, mặt đó bị chặn cho tới khi kiểm chứng lại.
- Giữ những CAD hợp lệ còn thiếu góc trong danh sách cần bổ sung. Chưa coi các bộ thiếu góc là đủ sáu hướng. Các hồ sơ tham khảo thiếu thông số/mã đặt hàng không được nâng thành mã đã xác nhận chỉ nhờ lần làm sạch tệp này.

## Kết quả kiểm tra

395 mục đang hiển thị, 1.332 tham chiếu mặt hợp lệ. Đã thử tám đường dẫn cũ của hai mặt cách ly: đều bị chặn. Đã đọc qua dịch vụ 36 tài sản DXF/preview của 18 tệp sửa: đạt. 44 bài kiểm tra backend đạt. API đã nạp bản cập nhật và health trả 200.

Không bổ sung mô hình CAD mới trong đợt sửa lỗi này; công việc bổ sung các góc nhìn còn thiếu vẫn chưa hoàn tất.

[Kết quả xác minh](verification.json), [nhật ký sửa và hash trước/sau](repairs.json). Thư mục `before/` và `quarantined-cad/` giữ các bản để đối chiếu, không nằm trong danh mục sử dụng.

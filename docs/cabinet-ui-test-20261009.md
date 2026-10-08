# Kiểm thử bóc tách → CAD → báo giá, 09/10/2026

- Giao diện local `/workspace/10`, PDF `2. SO DO TU DIEN (NHA NOI TRU).pdf`.
- Chạy bóc tách mới qua UI: 13 dòng, 26 cái. Chưa đạt đối chiếu nguồn: nhận một số CB nhánh thành MCCB; cầu chì ghi 1; chưa đầy đủ cụm đo lường.
- Bấm Báo giá & CAD: chưa tạo CAD; UI hiển thị form cần đối chiếu và thiếu layout/kích thước xác nhận.
- Catalog hiện có 835 bản ghi `source_cad_device_or_assembly`, không có bản ghi giá. Không thể coi báo giá là đầy đủ.
- Bấm Xuất BOM: UI báo báo giá gắn với kết quả bản vẽ. Chưa kiểm chứng đơn giá hoặc nội dung file tải.
- Sửa URL worker PDF để tránh phản hồi MIME cũ trong cache; build FE thành công, PDF mở lại trên UI không còn báo lỗi worker.
- 17 kiểm tra backend đạt: biến JSON, catalog đồng, CAD/quote isolated DB, nhãn và quy tắc hình học. W600 bị chặn khi không đủ khoảng CB→đồng; test bố trí dùng form W800 và CAD BKN/ABN250 chỉ định rõ.
- Biến d1–d8 đã nối phần bố trí; d9–d13 mô tả đầu vào cáp theo model; d14 và neo khóa/form chưa được xác nhận triển khai đầy đủ.
- Luồng UI tổng thể CHƯA ĐẠT. Cần sửa nhận dạng, hoàn thiện ánh xạ form và bổ sung giá có nguồn trước nghiệm thu.

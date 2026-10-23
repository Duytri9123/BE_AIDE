# Kích thước theo từng mặt CAD

Đã đo hình học của các mặt CAD hiện có và đưa số đo ngang × cao (mm) vào thông số của mặt đang chọn. Không suy ra chiều sâu từ một mặt, không thay kích thước thân trong catalogue bằng kích thước bao của bản vẽ.

| Hãng | Mục thiết bị | Tham chiếu mặt có số đo | Mục chỉ có một mặt đã đo |
|---|---:|---:|---:|
| ABB | 94 | 246 | 3 |
| LS Electric | 264 | 1.009 | 61 |
| CHINT | 37 | 79 | 18 |

Tổng cộng 395 mục, 1.334 tham chiếu mặt CAD. Các mã mặt thông dụng như `front`, `side`, `cover` được phân biệt theo ID hồ sơ thiết bị; không dùng mã mặt đơn lẻ để chuyển kích thước giữa các thiết bị. Một hình học CAD có thể được dùng lại trong nhiều mục hoặc mã hàng.

Chỉ đo DXF đã xác nhận đơn vị mm, không có lỗi audit. Bỏ chữ, thuộc tính chữ và điểm khỏi bao hình; không tự đo bản còn chứa thực thể ghi kích thước/đường dẫn chú thích. Cache giữ hash tệp và được kiểm tra lại trước khi tái sử dụng. Đã kiểm tra lại sau khi chạy trình tạo thông số để bảo đảm số đo vẫn được giữ. 40 bài kiểm tra backend đạt.

Đây là cập nhật số đo cho CAD hiện có, không phải một đợt bổ sung CAD mới. Đợt bổ sung CAD trước đó có 12 mặt LS (hai cụm đảo chiều AR-600, mỗi cụm sáu hướng) và 6 mặt CHINT NXM-250S 4P. Không đánh đồng cụm AR-600 với phụ kiện đơn lẻ trong bảng giá.

Số đo 2D không làm đầy các hướng nhìn còn thiếu: LS/CHINT vẫn còn 79 mục chỉ một mặt và 185 mục chưa đủ sáu hướng theo báo cáo kiểm kê. FE đã hỗ trợ thông số theo mặt trong commit cb858d01 đang triển khai; cập nhật này không cần thay đổi FE.

Chi tiết: [kiểm chứng dữ liệu hiển thị](cad-measurements-verification.json), [kết quả đo](cad-view-measurements.json), [kiểm kê mặt LS/CHINT](../ls-chint-view-counts-2026-10-21/view-count-report.md).

# Kết quả chạy thật với sơ đồ tủ E1

Ngày 24/11/2026. Dự án minh họa riêng: **Thiết kế E1 từ bản vẽ**, mã dự án 51. Xem tại [tab Thiết kế trong hệ thống cục bộ](http://127.0.0.1:5173/workspace/51). Tệp nguồn được nạp qua API upload, chạy bộ bóc tách của hệ thống và lưu kết quả ở phiên 175; sau đó chuyển thiết bị bằng nút của giao diện sang Tủ thiết kế.

## Kiểm tra bóc tách

Kết quả có 9 dòng dữ liệu và 11 thân thiết bị vật lý: một MCCB 3P 32A, bốn MCB 2P 20A, hai MCB 2P 30A, ba đèn báo pha và một cầu chì 2A. Hãng Schneider lấy từ ghi chú trên ảnh. Các mã LV510302 và A9F74220 là lựa chọn catalog để đối chiếu; không phải mã đọc được trên sơ đồ gốc. Khả năng cắt không ghi trong nguồn vẫn được giữ là chưa xác định trong thông số bóc tách.

Lượt đầu phát hiện lỗi khi ghép bảng giá vào `ExtractedDeviceSchema` vì thiếu trường `sku`. Đã bổ sung trường tương ứng, kiểm tra lại luồng typed device và chạy lại thành công. Không chỉnh dữ liệu dự án cũ để giả lập kết quả.

## Kiểm tra thiết kế trong giao diện

Phương án dùng vỏ W500 H700 D250 mm. Bố trí MCCB trên vùng giữa phía trên, sáu MCB cùng hàng DIN bên dưới, cầu chì bên trái và ba đèn trên cánh trong. Việc điều chỉnh được thực hiện bằng bảng thuộc tính của chính tab Thiết kế. Đã kiểm tra cả CAD 2D và view 3D, lưu và mở lại view.

- Có đủ 11 thiết bị và một thanh DIN trong bản lưu cuối.
- Bảy thiết bị dùng CAD có nguồn; bốn thiết bị là bao hình phương án gồm ba đèn và cầu chì.
- Mô hình không báo va chạm bao hình ở tư thế đóng. Chưa xác nhận hành trình cánh, gá/lỗ thực, đầu cos, tuyến dây, nhiệt hoặc khả năng bảo vệ điện.
- CAD iC60 và CVS hiện là hình học tham khảo theo họ. Quan hệ họ của hai mã được đối chiếu nguồn Schneider trong `app/data/design_learning_model_families.json`; không đánh dấu hình học lắp đúng biến thể đã xác minh.

## Kiểm tra cơ chế học

Kho lịch sử ghi sáu phiên lưu có thay đổi thiết kế. Giao diện hiển thị phạm vi duyệt, lý do, duyệt vào bộ nhớ, áp dụng bố trí đã học, cập nhật và thu hồi. Chưa có quyết định duyệt của người dùng cho ví dụ này, vì vậy bộ nhớ cá nhân có **0 mẫu được duyệt**, `accuracy=null` và không có dữ liệu ví dụ chạy thật tự động trở thành nhãn đúng.

20 kiểm thử hồi quy cô lập đã qua, gồm việc thứ tự ưu tiên CAD thay đổi sau duyệt, không tăng phiếu do gửi lại hoặc nhiều phạm vi, thu hồi, sửa hình học, phân quyền trước khi truy cập bộ nhớ, duyệt riêng thiết bị đã chọn, xung đột revision, ghi đồng thời và giữ bản đã commit khi JSON mirror lỗi. API thật trả 200 cho dữ liệu học dự án 51 và 404 khi cùng tài khoản yêu cầu dữ liệu học của dự án không thuộc quyền.

Frontend qua kiểm tra kiểu và production build, gồm prerender 124 trang. Backend cổng 8000 đã được khởi động lại với mã mới; frontend cục bộ cổng 5173 dùng backend này.

## Bằng chứng

Kết quả máy đọc: `outputs/design-learning-20261124/implementation-verification.json`. Bản lưu cuối, kết quả bóc tách, ảnh CAD 2D, ảnh 3D và ảnh bảng học cùng nằm trong thư mục này. Snapshot giữ revision và ID thiết kế để đối chiếu; không phải tài liệu phát hành chế tạo.

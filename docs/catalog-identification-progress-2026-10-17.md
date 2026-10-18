# Kết quả nhận diện toàn bộ thư viện CAD — 17/10/2026

Nguồn: thư viện phụ kiện DWG gốc và các DXF bóc từ thư viện. Không có BOM riêng. Công việc nhận diện chưa hoàn tất.

| Trạng thái | Hồ sơ |
|---|---:|
| Đọc được nhãn mã/dòng, đã đối chiếu tài liệu sản phẩm | 483 |
| Chưa tìm thấy nhãn mã trong dữ liệu chữ của CAD | 464 |
| Đọc được nhãn nguồn, còn cần tài liệu đối chiếu | 194 |
| Có chữ nhưng chưa có mã duy nhất | 186 |
| Chi tiết cơ khí theo quy cách | 111 |
| Bản vẽ hoặc cụm lắp đặt | 31 |
| Đã thấy mâu thuẫn nhãn với hình vẽ | 2 |

Tổng: **1471 hồ sơ**; **748 nhãn mã/dòng** có đối chiếu. Một hồ sơ có thể chứa nhiều nhãn thành phần. Các số này không có nghĩa đã xác định mã đặt hàng hay cấu hình điện.

Đã quét 2.073 lượt mặt DXF, đọc trực tiếp thuộc tính và tên block của DWG gốc. OCR thêm 670 mặt thuộc 513 hồ sơ ở thời điểm khởi chạy; không có lỗi OCR, kết quả máy đọc chưa tự trở thành chứng cứ xác nhận. Đã kiểm tra bằng mắt các nhãn BHA 44 trên hình 2 cực và BHA 34 trên hình 1 cực; hệ thống ghi rõ mâu thuẫn để tránh gán cấu hình theo nhãn tái sử dụng.

Đã đồng bộ thông tin vào hồ sơ gốc, dữ liệu xuất bản, chỉ mục tìm kiếm và thư viện HTML ngoại tuyến. Tìm kiếm hỗ trợ tiếng Việt không dấu, đổi thứ tự từ và cách viết mã có/không dấu nối; có ranh giới số để tránh NDK25 khớp NDK250.

Biến áp CHINT trong ảnh vẫn chưa đủ chứng cứ để chọn một model duy nhất. Tên block MBA - Chint và hình dáng không chứng minh NDK hoặc công suất cụ thể.

Chuyển đổi DWG sang DXF để đối chiếu hình học đã gặp tag số rỗng; cả bộ đọc thường và bộ khôi phục đều từ chối. Không dùng bản chuyển đổi lỗi để xác nhận danh tính. Đọc trực tiếp DWG và các DXF mặt hiện có vẫn thành công.

Kiểm tra bảo toàn: 0 thay đổi ở các trường định danh, thông số điện, CAD, auto_select và needs_review so với bản sao lưu trước đợt bổ sung; DWG gốc giữ nguyên: True.

Danh sách từng hồ sơ còn thiếu: [catalog-identification-remaining.json](catalog-identification-remaining.json). Bằng chứng nhãn: app/data/catalog_source_identification.json. Nguồn tài liệu và trang đối chiếu nằm trong từng hồ sơ; các hãng suy từ mã vẫn được đánh dấu ứng viên.

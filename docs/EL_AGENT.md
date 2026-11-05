# EL xử lý

EL là agent trong workspace, dùng các tool thật theo yêu cầu thay vì chạy một
checklist hiển thị cố định. Luồng hiện tại gồm bộ quyết định phía backend, bộ
thực thi API có ràng buộc dự án và cầu nối tới các tool CAD đang có trong browser.

## Tool đã nối

* Một tool đọc ảnh, PDF, DWG/DXF và tài liệu nguồn của dự án.
* 73 API nghiệp vụ được tìm từ OpenAPI ở thời điểm tích hợp: thông tin dự án,
  file, kết quả bóc tách, thư viện, thiết bị, tính BOM, xuất kết quả và các thao
  tác phân tích/tạo kết quả hiện có. Số lượng được cập nhật theo registry thực tế.
* 23 tool CAD từ `createCadTools()`, dùng lại executor hiện có của viewer.
  Khả năng thực thi còn phụ thuộc bản vẽ đang mở và quyền truy cập dịch vụ.

Registry chỉ nối các nhóm API nghiệp vụ được khai báo trong `el_tools.py`.
Không tự xuất API quản trị, tài khoản, credentials, thanh toán hay quyền xóa.
Tool mới ngoài các nhóm đó cần adapter/rule tương ứng, không chỉ thêm tên vào prompt.

## Cách hoạt động

EL chọn một tool hoặc trả lời trực tiếp. Khi gọi tool, frontend ghi hoạt động
đang chạy, thực thi tool thật rồi gửi kết quả lại để EL quyết định tiếp. Một
lượt được giới hạn 18 lần gọi; không có danh sách công đoạn hoặc phần trăm giả.
Các lời gọi tool không phải nội dung suy nghĩ nội bộ của model.

Hoạt động được lưu cùng phản hồi trong lịch sử chat trên trình duyệt, theo user
và project. Khi có file kết quả, UI cung cấp nút tải có xác thực. API thay đổi
dữ liệu thành công sẽ yêu cầu workspace tải lại file, phiên và thông tin dự án.

## Phạm vi và thao tác

* Server xác minh chủ dự án ở cả registry, lựa chọn tool và thực thi API.
* project_id được ràng buộc phía server; file, iteration, session và task được
  kiểm tra thuộc dự án. Browser kiểm tra route dự án trước khi dùng live CAD.
* Yêu cầu đọc/phân tích không cấp tool ghi. Tra cứu thư viện/catalog chỉ được
  đưa vào lựa chọn khi yêu cầu có phạm vi tra cứu đó. Cụm “bản vẽ” không được
  coi là lệnh “vẽ”. Không chỉ dựa vào lời hứa trong prompt để chặn thao tác ghi.
* Các quyền/số dư/entitlement do endpoint nghiệp vụ hiện có tiếp tục kiểm tra.
* Thao tác API ghi có receipt Redis theo user/project/run/tool/arguments để
  tránh chạy lại khi retry. Thao tác CAD cũng có receipt trong phiên browser.
* “Dừng EL” ngừng vòng quyết định và ngừng chờ. Job đã gửi cho worker có thể
  tiếp tục; EL không tự tuyên bố đã hủy job đó.
* Vòng quyết định hiện chạy khi tab đang mở; chưa phải agent nền bền vững khi
  đóng browser. Tác vụ đã enqueue vẫn dùng Celery/Redis hiện có.

## Các điểm tích hợp

* `GET /api/v1/chat/el/tools?project_id=...`: registry API nghiệp vụ có xác thực.
* `POST /api/v1/chat/el/next`: lựa chọn tool/câu trả lời dựa trên yêu cầu và kết quả.
* `POST /api/v1/chat/el/tool`: thực thi API đã đăng ký trong phạm vi dự án.
* `elToolBridge.ts`: schema và executor CAD dùng chung với CAD Agent hiện có.
* `elAgent.ts`: vòng gọi tool và callback hoạt động/file kết quả cho UI Vue.

Không cần cài thêm framework agent hoặc chuyển giao diện sang React cho thay đổi này.

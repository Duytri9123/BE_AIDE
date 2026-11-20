# EL xử lý

EL là agent trong workspace, dùng các tool thật theo yêu cầu thay vì chạy một
checklist hiển thị cố định. Luồng hiện tại gồm bộ quyết định phía backend, bộ
thực thi API có ràng buộc dự án và worker chạy nền độc lập với browser.

## Tool đã nối

* Một tool đọc ảnh, PDF, DWG/DXF và tài liệu nguồn của dự án.
* 73 API nghiệp vụ được tìm từ OpenAPI ở thời điểm tích hợp: thông tin dự án,
  file, kết quả bóc tách, thư viện, thiết bị, tính BOM, xuất kết quả và các thao
  tác phân tích/tạo kết quả hiện có. Số lượng được cập nhật theo registry thực tế.
* Luồng nền chỉ cấp công cụ đọc nguồn và API server, gồm API tạo file CAD.
  Công cụ thao tác trực tiếp trên editor vẫn thuộc luồng CAD trong browser;
  không giả lập editor khi người dùng tắt máy.

Registry chỉ nối các nhóm API nghiệp vụ được khai báo trong `el_tools.py`.
Không tự xuất API quản trị, tài khoản, credentials, thanh toán hay quyền xóa.
Tool mới ngoài các nhóm đó cần adapter/rule tương ứng, không chỉ thêm tên vào prompt.

## Cách hoạt động

Frontend gửi một lượt có request_id đến `/chat/el/runs`. Worker `aide_el` chọn
công cụ, thực thi và lưu checkpoint sau mỗi bước. Browser chỉ theo dõi trạng
thái; ngắt kết nối không hủy công việc. Không có giới hạn cứng 18 công cụ cho
toàn tác vụ; mỗi lần quyết định dùng tối đa 18 quan sát gần nhất.
Các lời gọi tool không phải nội dung suy nghĩ nội bộ của model.

Trước khi chọn công cụ, `POST /api/v1/chat/el/resolve` nối câu mới với tối đa
20 tin nhắn trước đó, gồm nguồn, kết quả và trạng thái từng lượt. Yêu cầu đã nối
ngữ cảnh được dùng thống nhất cho quyết định backend,
đọc nguồn và thực thi công cụ trong cả lượt. Backend `/next` cũng nối ngữ cảnh
khi client chưa thực hiện bước này. Câu hỏi bổ sung giữ đối tượng đang trao đổi;
thông tin mới được ưu tiên, còn đổi chủ đề hoặc hủy không tiếp tục lệnh cũ.
Không có bước đang chờ rõ ràng thì EL cần hỏi lại thay vì tự chạy lại việc đã xong.
Việc hiểu ngữ cảnh dùng mô hình AI, nên các lượt nối tiếp có thêm một lời gọi AI.

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
* “Dừng EL” yêu cầu tạm dừng. Worker hoàn tất bước AI/công cụ đang chạy, lưu
  kết quả rồi chuyển PAUSED; không bỏ kết quả hay hủy giữa chừng thao tác ghi.
  “Tiếp tục” dùng lại checkpoint và receipt, không chạy lại công cụ đã hoàn tất.
  Phạm vi tủ được kiểm tra khi tiếp nhận và giữ trên server để vẫn tiếp tục được
  sau thời hạn token chọn vùng, không mở rộng sang vùng chưa được xác nhận.
* Tắt máy người dùng/đóng tab không thay đổi trạng thái server. Mở lại dự án
  lấy lượt gần nhất theo user/project và gắn lại theo dõi, kể cả kết quả đã xong.
  Server, Redis và worker phải còn hoạt động.
* Checkpoint lưu trong `storage/el_runs.sqlite3` (thư mục cha UPLOAD_DIR), cùng
  volume bền vững với uploads; mọi API process và worker phải dùng chung volume.
  Không lưu bearer token. Worker tạo token nội bộ ngắn hạn cho mỗi bước API,
  kiểm tra lại tài khoản và quyền sở hữu dự án khi chạy/tiếp tục.
* Lease ngăn hai worker cùng chạy một lượt. Nếu worker gián đoạn giữa bước
  có thể ghi dữ liệu, yêu cầu kiểm tra kết quả trước khi người dùng tiếp tục.
  Lỗi được lưu để tiếp tục; không tự khẳng định mọi lỗi đều có thể bỏ qua.

## Worker nền

Trên Windows, `start_worker.ps1` tự gọi `start_el_worker.ps1` để mở worker riêng
cho queue `aide_el`. Worker phân tích/CAD giữ queue `aide_analysis,aide_cad`.
Không gộp các queue vào một worker solo: EL có thể chờ tác vụ CAD hoàn tất.
Trên server khác chạy thêm:

```sh
python -m celery -A app.tasks.celery_app worker --queues=aide_el --hostname=el@%h --concurrency=1 --loglevel=INFO
```

## Các điểm tích hợp

* `GET /api/v1/chat/el/tools?project_id=...`: registry API nghiệp vụ có xác thực.
* `POST /api/v1/chat/el/next`: lựa chọn tool/câu trả lời dựa trên yêu cầu và kết quả.
* `POST /api/v1/chat/el/tool`: thực thi API đã đăng ký trong phạm vi dự án.
* `POST /api/v1/chat/el/runs`: tiếp nhận tác vụ có request_id, chống gửi trùng.
* `GET /api/v1/chat/el/runs/latest?project_id=...`: khôi phục lượt gần nhất.
* `GET /api/v1/chat/el/runs/{id}?project_id=...`: theo dõi tiến độ/kết quả.
* `POST /api/v1/chat/el/runs/{id}/pause?project_id=...`: tạm dừng tại ranh giới bước.
* `POST /api/v1/chat/el/runs/{id}/resume?project_id=...`: tiếp tục cùng lượt.
* `elToolBridge.ts`: schema và executor CAD dùng chung với CAD Agent hiện có.
* `elBackground.ts`: gửi/theo dõi tác vụ server và callback kết quả cho UI Vue.

Không cần cài thêm framework agent hoặc chuyển giao diện sang React cho thay đổi này.

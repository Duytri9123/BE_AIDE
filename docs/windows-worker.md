# AI/CAD trên Windows

API và tác vụ nặng chạy trong các tiến trình riêng. Windows dùng Celery `solo`, concurrency=1; không cần đổi hệ điều hành. Worker xử lý một job tại một thời điểm: cấu hình này phục vụ hàng đợi có giới hạn, không phải 10.000 job đồng thời.

Từ workspace gốc chạy `& .\BE_AIDE\start_worker.ps1`. Worker chạy ẩn, nhận queue `aide_analysis` và `aide_cad`. Log/PID nằm ở `BE_AIDE/tmp/runtime/`. Các launcher backend/tunnel và launcher ẩn cũng gọi script này; API chạy hai Uvicorn worker.

## Hành vi

- `/analyze/stream` và `/analyze/generate-quotation-cad/stream` giữ định dạng SSE của FE nhưng chuyển tiếp tiến độ từ worker. Có heartbeat và header `X-Task-ID`.
- Đóng trình duyệt không tự hủy job đã tiếp nhận. `/analyze/task/{id}` chỉ cho chủ job xem/hủy.
- `/analyze/async-start` trả task_id ngay. Thiếu heartbeat worker trả 503; dự án có job trả 409; hàng đợi đầy trả 429/Retry-After.
- `/start` và `/generate-quotation-cad` giữ response cuối để tương thích. Dùng SSE hoặc async-start cho job dài để tránh timeout proxy.
- Mặc định `QUEUE_ANALYSIS_ENABLED=true`, `ANALYSIS_MAX_PENDING_JOBS=100` (gồm job chờ/chạy), metadata/result Redis hết hạn sau 24 giờ. Redis phải được vận hành tin cậy; dữ liệu này không tồn tại vĩnh viễn nếu Redis mất dữ liệu.
- Hủy theo cơ chế hợp tác giữa các công đoạn. Không dùng terminate=True với solo trên Windows. Job chờ bị đánh dấu sẽ được bỏ qua khi worker nhận.
- Worker lưu đúng schema, UUID/JSON, cập nhật session/iteration; trừ token bằng điều kiện SQL nguyên tử.
- Đối soát nhãn QF riêng biệt có thông số rõ ràng để giữ số lượng CAD. Không cộng tag lặp, tag mâu thuẫn hoặc nhiều panel.
- Cache thư viện CAD ngắn 5 giây; danh sách thiết bị dùng chung manifest trong một request. Thay đổi profile có thể chậm tối đa khoảng 5 giây để xuất hiện.
- Nếu không có CAD, response trả `success=false`, `cad_status=needs_review`, `cad_blockers`; Excel vẫn trả riêng nếu tạo thành công. Không tự điền kích thước hoặc duyệt form thiếu căn cứ.

## Kiểm thử

Chạy từ thư mục BE_AIDE:

```powershell
& .\venv\Scripts\python.exe scripts/test_queue_regressions.py
& .\venv\Scripts\python.exe scripts/test_queue_admission.py
```

Test admission dùng namespace Redis riêng và mock dispatch, không gửi AI thật. `verify_windows_queue.py` chạy worker/API thật với SQLite bản sao và Redis DB trống 14 hoặc 15, có gọi AI thật; kết quả trong `tmp/queue_fix_verification`.

## Giới hạn

Solo không cung cấp hard kill cho vòng CPU bị treo; deadline asyncio chỉ ngắt được thao tác có nhường quyền thực thi. Không tăng concurrency trên solo để kỳ vọng chạy song song. Muốn thêm capacity trên Windows cần các tiến trình worker riêng được quản lý, giới hạn RAM/rate-limit AI và đo tải lại. PostgreSQL, giám sát queue và worker chạy như dịch vụ tự khởi động lại chưa được cài đặt trong thay đổi này.

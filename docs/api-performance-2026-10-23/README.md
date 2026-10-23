# Rà soát API backend — 23/10/2026

## Phạm vi và giới hạn số đo

Đã lập inventory toàn bộ 155 khai báo API v1 trong source (154 ở endpoint modules và 1 ở api_router), kiểm tra trùng method + URL, phân trang, materialize dữ liệu, await trong vòng lặp, đọc file đồng bộ trong async, các quan hệ và truy vấn ở các điểm rủi ro. Không phát hiện trùng method + URL. Inventory không chứng minh các API tương tự về nghiệp vụ đã được hợp nhất.

`route-inventory-after.json` là inventory đầy đủ có file, function, dòng và cờ cần xem xét; `routes.md` trình bày từng route. Các cờ AST là tín hiệu rà soát, không tự động khẳng định lỗi. Nhóm enum/config nhỏ (hãng, nhóm, plan, provider) không mặc nhiên cần phân trang chỉ vì dùng `.all()`.

Chưa gọi toàn bộ 155 API trên production. Các POST AI/thanh toán/email/export không được gọi hàng loạt vì có thể tạo dữ liệu hoặc phát sinh chi phí. Không thể gán latency giả cho các route chưa chạy. Benchmark dưới đây đo tầng truy vấn bằng SQLite in-memory và dữ liệu tổng hợp, không bao gồm mạng, reverse proxy, xác thực hay tải production. Các test dùng DB riêng, không sửa DB hiện hành.

## Các lỗi đã sửa

| Điểm | Trước | Sau |
|---|---|---|
| Upload FE | Giới hạn tổng cố định 180 giây | Không giới hạn tổng khi còn tiến triển; ngắt sau 45 giây không có tiến triển; bước chờ xác nhận lưu tối đa 30 giây |
| Upload BE, project và user library | `await file.read()` nạp cả file vào RAM rồi ghi đè | Đọc từng 1 MiB, áp dụng MAX_FILE_SIZE_MB, ghi file tạm rồi replace; lỗi giữa chừng không ghi đè file cũ |
| GET analyze/project/{id}/sessions | 1 query lấy session + N query lấy toàn bộ iteration, SELECT mọi cột | Kiểm tra quyền project; JOIN session–iteration; 3 query cố định gồm kiểm tra quyền, COUNT và SELECT trang; mặc định 50, tối đa 100; chỉ lấy cột summary cần dùng |
| GET analyze/project/{id}/latest | Lấy toàn bộ session và mọi iteration của session mới nhất để chọn một | LIMIT 1 tại SQL; chỉ lấy cột cần; chọn revision usable mới nhất theo project, giữ chat_update rỗng hợp lệ; file CAD chọn mới nhất, LIMIT 1 |
| GET analyze/history/{session_id} | Không giới hạn lịch sử | Kiểm tra quyền project, phân trang 50/tối đa 100, bỏ cột prompt/raw response |
| GET payments/history | 1 query payment + mỗi payment một query tên plan | Một LEFT JOIN payment–plan, giữ 30 giao dịch và fallback plan đã xóa |
| GET admin-api/providers-summary | Query model trong mỗi provider | Lấy provider và batch model: 2 query, không tự tải connection/credential bằng relationship selectin |
| GET cad-agent/providers | provider_state được gọi từng provider, tải connection chứa credential dù chỉ cần kiểm tra tồn tại | SQL EXISTS kiểm tra connection khả dụng, batch model, 2 query; không chọn credential |
| GET providers / priority-models | Relationship selectin có thể tự tải connection ngoài nhu cầu | Chặn tải quan hệ thừa bằng raiseload, giữ model active cần dùng |
| GET projects/users/device-library models/browse | skip/limit không được chặn hợp lệ; model mặc định 2000 | Validate skip >= 0 và limit có trần; model mặc định 100, giữ trần 2000 cho consumer cũ |
| GET device-library/models | Lọc poles/current/icu sau LIMIT, có thể mất kết quả hợp lệ | JSON parameter predicates trong WHERE trước ORDER BY/LIMIT/OFFSET |

FE lịch sử có nút **Tải thêm phiên**. Danh sách không còn tải mọi phiên ngay lúc mở workspace. Upload giữ vòng tròn % thực, chỉ hiển thị 100% khi byte truyền đủ; không tự mở file/phiên sau upload.

45/30 giây là ngưỡng bảo vệ từng giai đoạn hiện tại, chưa phải SLA production đã được chứng minh. READ mặc định 15 giây vẫn tách khỏi upload; SSE/job không nên dùng deadline tổng của CRUD. Cần điều chỉnh bằng latency p95/p99 sau khi triển khai đo thực tế, đồng bộ timeout proxy/worker/provider, không tăng tất cả timeout để che truy vấn chậm.

## Số đo có thể lặp lại

Dữ liệu tổng hợp: 100 conversation_sessions, 1.000 analysis_iterations, 20 device/iteration và 24 KiB prompt/raw response mỗi iteration. Đo 5 lần; trước và sau cùng dữ liệu và cùng index, so sánh thuật toán đọc hiện tại với thuật toán cũ, không phải so sánh cả HTTP endpoint.

| Metric | Trước | Sau |
|---|---:|---:|
| SQL query | 101 | 3 |
| Iteration materialized | 1.000 | 50 |
| Trung vị | 135,49 ms | 9,03 ms |
| Chậm nhất trong 5 mẫu | 164,96 ms | 17,87 ms |

Chi tiết: `analysis-benchmark.json`. Số đo browser-data ở lượt trước: cold khoảng 2,38 giây, warm khoảng 0,15 giây, local; không thay thế số đo production.

## Quan sát toàn bộ API sau triển khai

Middleware thêm `Server-Timing: app;dur=..., db;dur=..., sql;desc="... queries"`. `app` tính đến response start; SQL time là thời gian driver thực thi, không bao gồm toàn bộ ORM deserialize. Log `api_slow` khi >= 1 giây gồm method, route template, status, total_ms, db_ms, sql_count, response_bytes. Không log query string, SQL parameters, credential hay payload. SSE: total_ms trong log là cả vòng đời stream; header đo đến response start. Chưa có histogram p95/p99 hoặc tracing các service không dùng SQLAlchemy (SQLite catalog riêng, file/Redis/HTTP ngoài không nằm trong db_ms).

## Điểm còn tồn tại, chưa được coi là đã giải quyết

| Ưu tiên | API/nhóm | Bằng chứng và việc cần làm |
|---|---|---|
| P1 | equipment-library/browse | SELECT record_json toàn bộ SQLite rồi lọc/group/slice Python. Cần read model chuẩn hóa, WHERE/FTS và grouping ở DB trước LIMIT; giữ tổng theo family đúng |
| P1 | device-library/browse | Eager-load mọi model + series/brand/category và CAD manifest trước khi lọc/phân trang. Cần projection/relationship index cho family–model–view, không chỉ thêm LIMIT sau khi đã nạp hết |
| P1 | cad-library/catalog-tb và preview/insert tương ứng | catalog_tb_manifest rglob mọi profile, đọc/hash preview mỗi lần, cả lúc cần một view. Cần asset index theo view_id, cập nhật lúc import CAD; request chỉ lookup một hàng |
| P1 | equipment-library/browser-data không có limit | Giữ contract full-data cho consumer workspace cũ; vẫn có thể trả toàn bộ. Cần chuyển các consumer sang projection/index/paging rồi bỏ full-data mặc định; không âm thầm cắt mất dữ liệu |
| P1 | projects/{id}/files, user-library/files, device-library/user-items | Chưa có paging, trả array đầy đủ. Cần thêm page API và UI tải thêm/virtualization đồng bộ trước khi chặn dữ liệu cũ |
| P1 | analysis_iterations | Bỏ raw prompt khỏi list nhưng summary vẫn đọc JSON device của tối đa 100 iteration để tính panel/count. Nên có summary được ghi cùng transaction, không tính lại từ mọi JSON lịch sử |
| P2 | cad-library list/catalog-tb, curated-library, catalog-prices/custom-prices, projection-catalog, workspace cad-candidates | Các payload list/manifest có thể lớn, một số không phân trang. Phân biệt metadata lookup cần đầy đủ với list UI; thêm projection fields và page contract |
| P2 | device-catalog | Có response paging và chạy sync read trong threadpool, nhưng vẫn build/merge catalog từ file toàn bộ mỗi request. Chuẩn hóa price_rows và liên kết, query theo index; cache theo revision chỉ là bước trung gian |
| P2 | models giới hạn tối đa 2000 | Giữ tương thích consumer cũ; mặc định đã giảm 100. Cần chuyển consumer bulk sang endpoint/search riêng rồi hạ trần |
| P2 | DB SQLite | busy_timeout=60s trong khi FE read=15s. Cần đo lock wait, giữ transaction ngắn và đưa CPU/file work ra ngoài transaction; không tăng timeout FE đồng loạt |
| P2 | Notifications/payment history | Đang cố định trang đầu 20/30; có trần nhưng thiếu cursor/skip để xem lịch sử sâu |
| P2 | POST async/AI/generate/export | Phải đo queue wait, worker run, outbound connect/read/write riêng; start/stream/prompt là contract khác nhau, chưa thể coi là route duplicate chỉ vì dùng cùng pipeline |
| P2 | Module startup | analyze import CAD engine singleton có load/index nguồn và Redis. Cần tách read router khỏi worker/generation imports hoặc warm-up có kiểm soát; latency cold khác warm |

Không có bằng chứng runtime rằng mọi cờ sync work trong async đều là bottleneck. Các POST đang phát sinh CPU/đọc file cần profiler/trace từng tác vụ trước khi chuyển threadpool/worker; không thay bằng async chỉ ở tên hàm.

## Thiết kế quan hệ và tách bảng

Đã có FK: projects → conversation_sessions → analysis_iterations, payments → plans, brand/category → series → model. Vì vậy sửa query JOIN/EXISTS/load_only trước; không tạo bảng trùng chỉ để đổi tên dữ liệu.

Đã chuẩn bị migration **d82f1a6b903e** với 5 composite index tương ứng project/session/iteration/file/payment filter và order. Migration chưa được áp dụng vào DB thật. Không tự migrate hoặc rebuild dữ liệu hiện hành.

Các phần nên tách ở bước schema tiếp theo:

| Bảng/read model | Quan hệ và mục đích |
|---|---|
| analysis_iteration_summaries | PK/FK iteration_id 1:1; device_count, total_quantity, panel summary, file display; list chỉ đọc bảng này; ghi atomically cùng iteration |
| analysis_iteration_details | iteration_id 1:1; prompt/raw response/thinking/validation JSON dung lượng lớn, chỉ đọc khi mở chi tiết/debug |
| analysis_devices | FK iteration_id; snapshot thiết bị theo iteration, panel_id nếu có, quantity/spec; tránh copy cùng payload qua nhiều API |
| iteration_files | FK iteration_id + project_file_id, unique cặp; thay việc phụ thuộc filename list trong JSON, vẫn giữ snapshot tên để truy vết |
| equipment_views | FK equipment_id; view_id unique, face, asset/revision/availability; preview lookup trực tiếp thay rglob/JSON scan |
| price_rows / catalog_documents | price_row FK document_id, manufacturer_id; SKU/spec/rating/edition/index searchable; schema catalog hiện có equipment(record_json) và FTS, các view vẫn lồng JSON |
| equipment_price_links | FK equipment/model/view + price_row, scope/review status/evidence; quan hệ nhiều–nhiều được xác minh, không tự gán giá/geometry chỉ vì model giống |
| ai_connections.provider | Hiện text indexed; nên mapping provider_id FK sau khi thống kê alias/orphan và migration dữ liệu, không thêm FK mù |

Migration schema lớn phải có backfill idempotent, đối chiếu số bản ghi/count/permission, dual-read kiểm chứng và cutover consumer. Đây là thiết kế đề xuất, chưa triển khai các bảng này; hiện chỉ có 5 index được chuẩn bị.

## Kiểm thử và chạy lại

- `venv/Scripts/python -m unittest scripts.test_analysis_reads scripts.test_api_performance scripts.test_library_reference_prices scripts.test_customer_equipment_information`
- `venv/Scripts/python -m scripts.benchmark_analysis_reads` (DB in-memory độc lập)
- `python scripts/audit_api_surface.py --output docs/api-performance-2026-10-23/route-inventory-after.json`
- `node AIDE/packages/cad-viewer-example/scripts/test-upload-timeouts.cjs` từ workspace root.

28 test backend đạt; test FE upload progress/inactivity/save timeout và cleanup đạt; Vue compile hai component thay đổi đạt; migration sinh đủ 5 CREATE INDEX bằng offline SQL. Typecheck toàn FE có 26 diagnostic chuẩn hóa giống lượt trước, không có diagnostic mới (test globals, type icon, OrbitControls, unused declarations). Hai test search ở test_catalog_query_matching đã thất bại ở lượt trước, không được sửa trong audit này. Chưa triển khai website hay chạy migration production.

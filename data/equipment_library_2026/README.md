# Thư viện thiết bị AIDE 2026 cho AI

`equipment_catalog.jsonl` là nguồn đọc chính: mỗi dòng là một JSON độc lập và có `catalog_id` bền vững. Giá được giữ theo từng dòng PDF; Mitsubishi dùng 3.140 dòng chi tiết thay vì 1.976 dòng gộp để không mất biến thể. `equipment_groups.jsonl` nhóm các dòng theo hãng/loại/model, kèm ID biến thể. `cad_assets.jsonl` lập chỉ mục toàn bộ CAD trong bản DWG nguồn và các CAD được bảng thiết bị dẫn tới.

Đường dẫn `path` đều tương đối với `Tudien/CATALOG_PHU_KIEN_DOC_LAP`. AI nên dùng `record_type`, `cad.status`, `cad.match_basis` và `warnings` trước khi chọn thiết bị. `family_or_frame_cad` không chứng minh đúng SKU; `source_cad_unverified_sku` chỉ chứng minh bản vẽ nguồn. Giá `null` nghĩa là chưa có dòng giá trong tài liệu đang dùng.

SQLite có bảng `equipment`, `cad_assets` và chỉ mục toàn văn `equipment_fts`. Ví dụ: `SELECT e.catalog_id,e.model,e.cad_status FROM equipment_fts f JOIN equipment e ON e.catalog_id=f.catalog_id WHERE equipment_fts MATCH 'BKN';`. Xem `manifest.json` để kiểm tra phiên bản, số bản ghi và SHA-256 của từng dữ liệu nguồn.

Tra cứu cho AI: `python BE_AIDE/scripts/query_equipment_library.py BKN --brand LS --cad available --limit 10` trả về JSON chứa đầy đủ thông số, giá, căn cứ CAD và đường dẫn nguồn. Kiểm tra: `python BE_AIDE/scripts/verify_equipment_library.py`.

Backend đọc trực tiếp SQLite qua `app.services.equipment_library`. API: `GET /api/v1/equipment-library/manifest`, `GET /api/v1/equipment-library/search?q=BKN&brand=LS` và `GET /api/v1/equipment-library/{catalog_id}`. Bộ xử lý giá chỉ dùng dòng PDF 2026 khi mã và các thông số yêu cầu dẫn tới đúng một biến thể; các dòng còn mơ hồ giữ nguyên trạng thái cần đối chiếu. Trường `cad.status` luôn đi kèm kết quả.

Bản sao dữ liệu máy đọc được lưu trong `BE_AIDE/data/equipment_library_2026` để backend vẫn tra cứu được khi chỉ checkout repository backend. Các tệp DXF/DWG nguồn nằm trong thư viện `Tudien` riêng; API bổ sung `available_now` trên mỗi đường dẫn CAD để báo tệp có thực sự hiện diện ở môi trường đang chạy hay không.

Chạy lại: `python BE_AIDE/scripts/build_equipment_library.py` sau khi cập nhật các bảng hãng hoặc `THIET_BI_KHAC_2026/products.json`.

# Danh mục vỏ tủ trống

Ứng dụng chỉ đọc `curated_manifest.json`. Chỉ mục gốc `manifest.json` và DXF nguồn được giữ để đối chiếu; các mẫu trong `excluded_manifest.json` không thể chọn hoặc tạo CAD qua API.

Quy tắc lọc: có kích thước H × W × D hợp lý, phân loại trong nhà/ngoài trời, file DXF có hình học, không có nhãn bố trí thiết bị và không có block thiết bị điện nhận diện được. `scripts/curate_empty_cabinet_templates.py` tạo lại hai danh sách và ghi lý do loại từng mẫu.

Đây là bước sơ tuyển dữ liệu bản vẽ vỏ tủ. Chỉ mục nguồn không có đủ bằng chứng thử nghiệm để khẳng định đạt IEC 61439, cấp IP/IK hay khả năng chịu nhiệt/ngắn mạch. Các thuộc tính đó cần hồ sơ kỹ thuật của nhà sản xuất trước khi ghi là đạt chuẩn.

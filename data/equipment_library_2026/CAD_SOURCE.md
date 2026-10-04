# CAD phụ kiện 2026

`equipment_catalog.sqlite` là catalog đang dùng trong trang thư viện. Chế độ mặc định hiển thị 4.445 dòng bảng giá 2026, 641 bản ghi `source_cad_device_or_assembly` được bóc tách từ `THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg`, và 2 bản ghi tham chiếu. Bộ lọc nguồn cho phép xem riêng từng loại.

SHA-256 của DWG nguồn: `cd7c2afc417061349d0f94a95574bf4326df876a4ca60fdaaef0396849dc9bc9`. Giá trị này trùng `source_dwg_sha256` trong `Tudien/CATALOG_PHU_KIEN_DOC_LAP/full_accessory_cad_inventory.json`.

`source_cad_assets.zip` chứa 1.484 file DXF/ảnh xem trước mà toàn bộ catalog đang tham chiếu, gồm CAD của dòng bảng giá và CAD bóc tách từ DWG nguồn. Backend đọc file trong gói này trước, để việc xem và tải CAD không phụ thuộc vào thư mục Tudien bên ngoài. Có thể tái tạo gói bằng `scripts/package_equipment_library_assets.py` khi DWG và catalog được cập nhật.

Các tên đọc từ CAD chưa tự động trở thành mã hàng chính xác. Trạng thái đối chiếu được giữ trong trường `cad.status` của từng bản ghi.

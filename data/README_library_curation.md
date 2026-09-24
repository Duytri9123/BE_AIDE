# Thư viện CAD phục vụ bố trí tủ

- Nguồn đọc: thư viện hãng hiện có, TỔNG HỢP 1 và FOMTU.dwg; FOMTU.bak được kiểm kê riêng. Không sửa file gốc.
- Chỉ đưa thành phần có loại xác định vào danh sách chèn. Khung tên, bảng chứa nhiều thiết bị và block chưa nhận dạng không phải thiết bị.
- FOMTU có 265 block được giữ trong bản phân phối; các bản xuất chưa phân loại nằm trong tmp/formtu/excluded_exports trên máy xử lý.
- 955 hình nguồn được chọn, gom 727 nhóm CAD. Các mục catalog còn giữ thông số đặt hàng riêng.
- Các mặt CML/KDE có quy ước hậu tố đã đối chiếu với bảng nguồn. Không suy đoán hướng nhìn bằng tỷ lệ hình chữ nhật. Mặt chưa rõ ghi Hình nguồn.
- Đèn đỏ/vàng/xanh dùng tên tiếng Việt và gom hình dùng chung giữa nguồn; việc dùng chung hình không xác nhận thông số điện hay mã đặt hàng tương đương.
- Block Tu 30KVAR là tụ bù, không phải vỏ tủ. Block Tu 40KVAR chứa chữ 50kVAr nên tên nguồn chưa được dùng làm thông số xác nhận.
- Báo cáo catalog_cad_sync_audit.json: khớp tên hoặc series chỉ là đầu mối đối chiếu, chưa tự gắn bản vẽ cho model.

## Dữ liệu cần trước khi tự bố trí vỏ tủ

Mỗi model cần kích thước mm được xác nhận, khoảng hở trái/phải/trên/dưới/trước/sau, hướng lắp và điều kiện nhiệt, vùng đấu dây và bán kính uốn cáp, nguồn tài liệu đúng model. API trả mounting_profile_status để hiển thị phần còn thiếu. Kích thước hình bao hoặc trạng thái có CAD không chứng minh đủ điều kiện bố trí.

Luồng Tạo CAD dùng nguyên form trong `data/cabinet_templates/formtu`, không gọi bộ dựng GA-01. Có 339 khung nguồn, giữ cả các mục chưa phân loại/chưa có kích thước. Loại tủ lấy từ thuộc tính khung tên; không suy đoán loại từ hình dáng. Chọn theo H × W × D và loại tủ; ưu tiên form gần nhất có đủ mốc đổi những chiều đang thay đổi. Các form không đủ mốc vẫn có trong danh sách xem nguồn.

Co giãn dựa trên điểm đầu/cuối DIM của từng hàng/cột mặt, khoảng hiện tại 75–125% kích thước gốc. Các đường bao đi qua trục co giãn được kéo dài; chữ, vòng tròn và block phụ kiện nhỏ giữ kích thước. Vùng kích thước chồng nhau bị chặn để tránh ghi số đo mới lên hình chưa điều chỉnh. Đây chưa phải bộ ràng buộc gia công cho mọi biến thể. Bốn bản xuất có chênh lệch số đối tượng được đánh dấu cần kiểm tra và không được tự chọn.

Tên sản phẩm tùy chọn thay chữ VỎ/VÕ TỦ; để trống sẽ bỏ chữ này. Bản chèn gồm các hình nguồn và khung tên trong một block Model, chờ người dùng chọn tâm, Esc hủy. DXF chèn chuyển DIM thành đường/chữ đã cập nhật và ATTRIB thành TEXT để trình xem đọc được; DXF nguồn giữ DIM gốc. XData lưu mã form cùng kích thước yêu cầu. File nguồn DWG/BAK không bị sửa.

Tái lập thư viện: `python scripts/extract_cabinet_templates.py` dùng bản chuyển đổi `tmp/formtu/formtu.dxf`. Chạy `python -m unittest scripts.test_cabinet_templates` để kiểm tra mẫu 1500 × 1400 × 450 từ form 1600 × 1400 × 450 và mẫu ngoài trời 1000 × 600 × 350. Bộ xuất phải gọi `post_bind_hook` cho DIM đã sao chép trước khi lưu, nếu không thư viện ezdxf giữ đồ họa ở bộ nhớ tạm rồi làm mất khi mở lại.

## Nạp và kiểm tra

Chạy scripts/build_cad_component_catalog.py rồi scripts/seed_devices_catalog.py bằng Python của backend. Chạy scripts/audit_catalog_cad_sync.py để cập nhật báo cáo đối chiếu. Kiểm tra: unittest scripts.test_device_families scripts.test_library_cad_links scripts.test_device_preview; frontend Playwright library-cards, cad-library-insert, cad-library-palette.


## Cập nhật catalog và đặt thiết bị

- Danh sách CAD lấy từ API device-library; ID model và SKU là khóa quản lý. Chọn đúng mã trong nhóm biến thể trước khi đặt.
- Quản trị viên mở chi tiết thiết bị → Cập nhật catalog để sửa kích thước và chọn hình CAD từ thư viện. API PATCH model-details lưu vào device_models, tăng catalog_revision và ghi người sửa, thời điểm, nguồn đối chiếu. Revision cũ trả 409, không ghi đè cập nhật mới.
- Seed giữ kích thước và liên kết CAD đã sửa thủ công. Không tự xác nhận độ chính xác kỹ thuật khi lưu. Catalog DB của thư viện chưa tự xuất ngược sang catalog_data.json dùng bởi bộ báo giá; không coi hai nguồn đã đồng bộ hoàn toàn.
- Kéo vào bản vẽ hoặc bấm Đặt chuyển sang xem trước hình bao; bấm tọa độ để chốt, Esc hủy. Chèn hình nguồn giữ XData AIDE_CATALOG_MODEL (modelId, sku, assetId); đặt hình bao giữ modelId và SKU. Bản vẽ đã đặt là snapshot, không tự đổi hình học khi catalog được sửa.
- Thư viện form tủ có manifest riêng theo mã khung nguồn; không trộn khung tên vào danh sách model thiết bị điện.

# Trình tự thiết kế và khoảng cách theo CAD nguồn

1. Bóc tách chỉ nhận dạng thiết bị, thông số, tag, số lượng, mặt thao tác và nguồn bằng chứng. Không chọn form hoặc CAD cuối cùng tại bước này.
2. Khi bắt đầu thiết kế: mở lại CatalogTB hiện tại; chọn đúng họ/mã/cực, mặt lắp, mặt bên và mặt thao tác. Không đổi CAD họ thành mã hàng chính xác khi chưa có bằng chứng.
3. Tính bao hình theo mặt và số thân thực tế; thêm không gian đầu nối, uốn dây, nguồn vào, xương cá, bản lề và thao tác theo phương án. Bao hình nét vẽ không phải bản đồ lỗ gá.
4. Từ không gian cần thiết mới xét các form trong CatalogTB/Form tủ. Kiểm tra vùng hữu dụng từng mặt, hèm, đố/tấm gá và chiều sâu. Không lấy kích thước tổng trừ mặc định 70/100 mm.
5. Căn thiết bị và các hình chiếu theo tâm lắp/thao tác có bằng chứng. Không mặc định khe 35 mm và khoảng hàng 45 mm. MCB mô-đun có thể liền nhau; vẫn phải kiểm tra điều kiện nhiệt và đấu dây của model.
6. Kiểm đếm từng tủ, kiểm tra chồng lấn, chiều sâu, đủ mặt, đầu nối, quỹ đạo cánh và đối chiếu DWG mẫu. CAD rà soát không phải CAD duyệt chế tạo.
7. Chỉ thiết kế đạt mới mở báo giá. Excel chỉ sinh khi người dùng tải báo giá.

## Dữ liệu khoảng cách

Form lưu `placement_rules` theo `mounting_plate`, `inner_door`, `outer_door`: `verified`, `source_handles`, `left_mm`, `bottom_mm`, `right_mm`, `top_mm`. Giá trị là khoảng chừa thực tế theo hệ tọa độ mặt đó; nguồn cáp có thể làm các mép không đối xứng.

Thiết bị lưu `verified_placement_clearance`: `verified`, `source_reference`, `horizontal_mm`, `vertical_mm`. Các giá trị chưa xác minh không được coi là khoảng cách chuẩn.

## Đo mẫu 457

Đường DIM nguồn xác nhận thân PX1 H900×W600×D250 và PX2 H700×W500×D250 mm, khớp ô C21/C39 báo giá. DWG có bệ riêng 100 mm, trong khi báo giá ghi treo tường. Không cộng bệ vào chiều cao thân hoặc sao chép bệ thành cấu hình báo giá đã duyệt.

Mặt SIDE có DIM 901/701 mm (handles 1106067/11062D6), lệch 1 mm so với EQUIPMENT/E-SIDE 900/700. Giữ cờ đối chiếu; không âm thầm chuẩn hóa dữ liệu nguồn. Hèm, mái, tấm gá và phần nhô phải kiểm tra riêng theo từng mặt.

Theo nét hiển thị trong DWG mẫu: timer 74×120 mm; mặt bên 43×120 mm. BKN 1/2/3P rộng 18/36/54 mm, cao 81 mm, chiều sâu hình chiếu 81,3 mm. Cụm chuyển mạch có khoảng tâm ngang 60 mm; bao hình mặt trước rộng 35,445 mm nên khe nét 24,555 mm. Một số mô-đun BKN/cầu đấu đặt liền nhau, khe nét 0 mm.

Các con số là đo CAD dự án, không thay tài liệu lắp đặt nhà sản xuất. Nguồn 97×141 mm đang dùng hình chiếu bên trên mặt tấm lắp; không tự đổi thành mặt trước. Các phần đã explode phải đo riêng, không dùng danh sách INSERT để tuyên bố đủ toàn bộ thiết bị.

Bằng chứng từng handle, từng mặt và khoảng cách nằm tại `outputs/sample-cad-recovery/source-spacing-audit.json` trong workspace. Không chuyển mọi khoảng đo này thành quy tắc chung cho tủ khác.

## Bổ sung dữ liệu nhà sản xuất và kiểm tra nhận diện

NCH8-20/25 2P đã bổ sung mặt trước và mặt bên từ PDF vector CHINT chính thức. Chiều dài tổng 85 mm khác chiều dài thân 82 mm; không bỏ phần nhô khi tính bao hình. Giữ riêng kích thước ghi trên tài liệu và kích thước vector: mặt bên đo được khoảng 66,618 mm, trong khi DIM danh nghĩa là 66,5 mm. Hồ sơ chưa duyệt chế tạo hoặc cấu hình cuộn hút/tiếp điểm.

Tài liệu LS chính thức tháng 09/2024 trang 4 xác nhận LA63N 6 kA và LA63H 10 kA; hình 1P ghi rộng 17,6 mm, cao thân 83 mm và chiều sâu 72 mm. Không đổi tên CAD BKN 18×81 mm thành LA63. Chưa có bằng chứng CAD đầy đủ cho mọi cấu hình 2P/3P, phần nhô và lỗ gá. Báo cáo: `outputs/sample-cad-recovery/LA63-official-evidence.json`.

Nhãn cũ `Asia` được chuẩn hóa thành `Asian` khi chọn hình, lưu lại `source_brand_label`. Đây là nhãn chưa xác định hãng, không dùng làm bộ lọc nhà sản xuất. Nếu đã có CAD nhưng thiếu mặt bên/bao hình, báo `matched_cad_missing_envelope` và lưu danh sách CAD đã tìm thấy; không báo thiếu thiết bị hoặc tự điền chiều sâu.

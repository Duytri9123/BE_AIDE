# Thiết kế theo chức năng, phụ kiện và khối mặc định — 24/11/2026

Đã triển khai trong luồng **Bóc tách → Tủ thiết kế**, không chỉ là bản sửa tọa độ cho E1. Phiên bản quy tắc: `functional-cabinet-v2`. Mọi phương án mới vẫn phân biệt thiết kế cơ khí tham khảo với xác nhận điện/chế tạo.

## Chính sách người dùng

- Không chỉ định hãng aptomat: ưu tiên LS. Đã có hãng/mã nguồn: giữ nguyên yêu cầu điện. Nếu thiếu khối, dùng hình học mặc định nhưng lưu riêng hãng hình học và hãng yêu cầu; không biến hình LS thành bằng chứng sản phẩm Schneider.
- Cầu chì, đế cầu chì, cầu đấu, đèn báo, chặn DIN có thể dùng chuẩn dùng chung khi chưa chọn mã/hãng. Thiếu mã không đồng nghĩa thiếu chi tiết vật lý. Cầu chì được lưu thành cụm đế + ruột, không tính thêm hai thiết bị độc lập trên panel.
- Trường hợp E1: một ký hiệu cầu chì nguồn cấp ba đèn báo pha được giữ nguyên trong số lượng nguồn. Phương án thêm hai cụm cầu chì2A để bảo vệ riêng từng pha, ghi rõ là bổ sung thiết kế, không sửa số lượng bóc tách thành dữ kiện gốc. Bó dây từ panel sang cánh được lưu riêng, chờ xác minh đầu cực và đoạn mềm qua bản lề.
- Không tự ghi tên FU1, dòng định mức hoặc tên từng thiết bị lên mặt thiết kế. Thông tin nằm trong bảng thiết bị, BOM và báo cáo. Nhãn CAD gốc thuộc khối nguồn được giữ nguyên.
- Các lần xuất hiện khác nhánh không bị gộp mất định danh khi chung mã. Lưu riêng occurrence, tải, pha, tag và yêu cầu nguồn; có thể dùng chung hình học.

## Đọc thư viện và giới hạn bằng chứng

`scripts/study_cabinet_forms.py` đã đọc 110 hồ sơ `bo_tri_goc.json` (catalog có 108 vỏ hoạt động, 2 vỏ loại trừ), toàn bộ danh mục 297 vỏ `formtu`, và phân tích INSERT/bounding box trong 28 DXF được lấy mẫu theo loại/kích thước. Kết quả có đường dẫn và SHA256 trong `outputs/cabinet-engineering-v2-20261124/form-study.json`.

Các tên khối xuất hiện nhiều gồm BKN-LS, ABN100AF-LS, MCCB ABB A1, CHINT Light, sứ kẹp thanh cái, cầu tiếp địa, PNE-bar, VTPK_DUCT, contactor LS và fuse. Đây là số lần xuất hiện trong sheet, có thể bao gồm nhiều hình chiếu và chi tiết tham khảo ngoài mặt lắp; không phải số lượng BOM hoặc mẫu đạt để AI tự học.

Đã xem ảnh ghép tám sheet thuộc nhiều kích thước: 700×500, 800×600, 1000×800, 1200×800, 1400×800, 1600×800. Các bản vỏ sạch chủ yếu chứa kết cấu/cánh, không chứa đầy đủ thiết bị như danh sách occurrence. Không suy vị trí thực từ insertion point của khối động hoặc từ preview vỏ sạch. Trong 28 DXF legacy lấy mẫu, hai tệp có tên khối điện được nhận diện; khoảng cách hình học quan sát được không được biến thành khoảng cách hãng hoặc quy tắc chung.

| Nhóm tham khảo | Hồ sơ ví dụ | Điều rút ra có thể áp dụng | Điều không được suy ra |
|---|---|---|---|
| Vỏ 2 cánh nhỏ | 735f6abb77751a37-434 | Tách mặt cánh và panel, lấy contour lắp hữu ích từ nguồn | Không lấy 500×700 làm toàn vùng bắt vít |
| Nhiều nhánh BKN/ABN | 00c63f115a129caf-10E5E99, 10E72BD | Cần hàng môđun và vùng phân phối, thêm hàng khi số nhánh tăng | Không lấy số block làm số CB vật lý |
| Có contactor | 00c63f115a129caf-10E6F56 | Nhóm chức năng đóng cắt/điều khiển và bộ gá riêng | Không tự ghép relay vào contactor khác họ |
| Nhiều sứ/đồng | 142a10f4b2c12273-108CD58, 108CD77 | Tính vùng thanh cái, gá đỡ, đấu cáp riêng | Không suy dòng chịu tải từ kích thước ảnh |
| MCCB tổng/nhánh lớn | 142a10f4b2c12273-108CDB5, 108CDD4 | Tách CB tổng, nhóm nhánh và đường cáp; đánh giá sâu tủ | Không tự chứng nhận phân khoang từ số cửa |

## Luồng thiết kế mới

1. Giữ yêu cầu nguồn và thứ tự nhánh, nhận diện thiết bị trên cánh / panel / phụ kiện tích hợp.
2. Tìm CAD tương thích; khi thiếu, áp dụng chính sách mặc định. Khối minh họa 3D có thân, vít, cần gạt, đế gá, thanh đồng/đế cách điện. Giữ bao hình riêng để không phình kích thước lắp.
3. Phát sinh BOM thiết kế: máng dọc/ngang, đầu ra từng cực, điểm phân phối pha, N/PE, DIN và chặn. Các phần này mang `origin=design_added`; không thêm vào số thiết bị đã đọc từ nguồn.
4. Bố trí theo tầng chức năng. Dành vùng cho N/PE, đầu nối ra, hàng nhánh, CB tổng/phụ trợ; đèn trên cánh trong khi vỏ có hai cánh. Không suy MCCB là thiết bị gài DIN.
5. Lấy contour hữu ích từ CAD thật; thử cỡ có sẵn và cỡ được bộ resize nguồn tạo lại, ưu tiên thể tích nhỏ hơn trong tập ứng viên. Thử tăng chiều cao/rộng/sâu riêng trước khi tăng cả ba. Từng phương án phải chứa cả phụ kiện, vùng đấu dây và thỏa kiểm tra bao hình đóng. Không chỉ cộng diện tích/chiều rộng MCB để chọn tủ.
6. Lưu kết quả thử cỡ và lý do chọn trong `engineeringReport.sizeTrials`; xem ở **Hoàn thiện & vật tư**, xuất BOM CSV và hồ sơ JSON.
7. Lập graph/tuyến dây minh họa theo cổng của khối chuẩn và vùng máng. Chúng được đánh dấu `standard_port_assumption_not_verified_sku`; chưa phải sơ đồ từng chân được chứng nhận. Sau chỉnh vị trí/đổi khối, xóa tuyến cũ để tránh hiển thị dây sai. Không tự khoan đầu cáp khi hướng cáp chưa xác nhận.
8. Chỉ người dùng duyệt mới tạo mẫu học. Không dùng lần lưu, số lượng mẫu hoặc trạng thái không va chạm để tuyên bố tăng độ chính xác.

Các khoảng 35 mm, máng25×40 và dự phòng20% là giá trị khởi tạo phương án có thể đổi, không phải khoảng cách/định mức phổ quát. Cỡ được chọn mới đạt điều kiện bố trí; nhiệt, vật liệu, IP, ngắn mạch và yêu cầu bảo trì vẫn là điều kiện cần kiểm tra.

## N và PE: tách chiều dài, số đầu nối, tiết diện và định mức

Chiều dài mô hình theo số điểm đấu + dự phòng + khoảng hai đầu. N tính đầu vào, các nhánh và mạch phụ; PE tính đầu vào, các nhánh, vỏ và cánh. Không gộp N và PE thành một thanh mặc định.

- **N**: lưu dòng yêu cầu theo CB nguồn, xem tải không cân bằng và hài bội ba, điều kiện nhiệt, dòng từng đầu nối. Không tự giảm N khi chưa có căn cứ. Với dây Cu pha≤16mm², lưu mức N tối thiểu bằng dây pha trong phạm vi phương pháp áp dụng; trường lớn hơn/thiếu vật liệu giữ chưa xác định.
- **PE**: không lấy dòng làm việc của CB để tính mật độ dòng PE. Lưu quy tắc dây cùng vật liệu: pha≤16→PE bằng pha; 16<pha≤35→PE16; pha>35→PE bằng nửa pha. Kiểm tra thêm phương pháp đoạn nhiệt `S=I√t/k`, cơ khí, trở kháng vòng sự cố và liên kết vỏ/cánh theo điều kiện áp dụng.
- Kết quả trên là **tiết diện dây**, không được chép thành tiết diện thanh đồng. Tiết diện đồng và định mức thanh đang để `null`/chưa xác minh; chọn theo catalog định mức đã kiểm chứng hoặc tính nhiệt/chịu ngắn mạch, số/loại đầu cốt, khoảng cách vít và sứ đỡ. Hình thanh có vít là mô phỏng, không là bản gia công.

Ví dụ datasheet Hager KN10N ghi 10 điểm, 63A, 45×33×34mm: đó là dữ liệu của đúng cụm đầu nối ấy, không chứng minh mọi thanh cùng kích thước đều chịu63A và không được nhân dòng bằng số thanh mắc song song.

Nguồn: [LS MCB catalog](https://www.ls-electric.com/upload/customer/download/1402/LVCB.pdf), [Schneider — sizing neutral](https://www.electrical-installation.org/enwiki/Sizing_the_neutral_conductor), [Schneider — sizing PE](https://www.electrical-installation.org/enwiki/Sizing_of_protective_earthing_conductor), [Hager KN10N datasheet](https://assets.hager.com/step-content/P/PDS_157331990000EN/Document/std.lang.all/PDS_KN10N_0000_en-GB.pdf). Công thức tóm tắt không thay các điều kiện đầy đủ trong tài liệu nguồn/tiêu chuẩn áp dụng.

## Học từ chỉnh sửa đã duyệt

Thêm phạm vi **Bố trí và khối mặc định dùng chung** (`assembly_layout`). Phạm vi này lưu hình học, loại/cực/dòng, nguồn CAD hoặc khối chuẩn, yêu cầu hãng, tải/chức năng, vỏ, cỡ tủ và vị trí đã duyệt. Nó không tạo nhãn “CAD đúng SKU” cho khối dùng chung.

Chỉ tái dùng khi cùng vỏ/cỡ, bộ yêu cầu và dấu vân tay hình học. Khác định mức/khối hoặc còn va chạm/vượt biên thì từ chối. Mẫu chỉ thuộc chủ sở hữu đang có quyền; có thể thu hồi; mẫu sửa sau duyệt cần duyệt lại. Khi áp dụng vẫn kiểm lại cơ khí và vô hiệu tuyến dây cũ nếu vị trí đổi. Thiết kế khác tiếp tục chạy bộ bố trí theo chức năng và chọn cỡ; không ngoại suy mù từ tọa độ E1.

## Giới hạn hiện tại

Chưa có tự động chứng nhận nhiệt, ngắn mạch, phân khoang hay danh sách dây từng chân đã xác minh model. Mô hình tuyến dây là minh họa. Nguồn E1 vẫn chưa xác nhận cáp đầu vào; tổng32A cần kiểm tra đồng thời tải phaA/B. Các phụ kiện nội bộ từ bóc tách được giữ trong báo cáo chờ liên kết đúng thiết bị chủ, không bị mất hoặc đặt thành khối độc lập tùy tiện. Không phát sinh contactor/relay không có chức năng nguồn yêu cầu.

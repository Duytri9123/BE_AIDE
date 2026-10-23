# Cập nhật thư viện Schneider — 21/10/2026

Đã rà toàn bộ 240 mục/304 mặt ban đầu, hồ sơ Schneider trong thư mục hãng và các nhóm chức năng, cùng 4.414 dòng bảng giá Schneider. Không dùng ảnh CAD để suy dòng cắt, tỷ số điện, cực bảo vệ hay mã đặt hàng.

## CAD mới đã nhập

| Bộ CAD | Mã đối chiếu bảng giá | Số mặt | Thông tin kỹ thuật |
|---|---|---:|---|
| MCADFD0000998, Acti9 iC60N 1P | A9F74150 | 6 | 50 A, đặc tuyến C; Icn 6 kA tại 230 V AC theo IEC 60898-1; Icu 10 kA tại 220–240 V AC theo IEC 60947-2 |
| MCADPD0004675, TeSys LRD | LRD21 | 6 | Chỉnh định 12–18 A, cấp tác động 10A; 1NO + 1NC; lắp dưới contactor tương thích, gá riêng cần phụ kiện |

Mỗi bộ có trước, sau, trái, phải, trên và dưới. Nhãn trên giao diện chỉ dùng tên mặt ngắn. Giữ toàn bộ nét thiết bị của từng CAD hãng; không tạo mặt còn thiếu bằng mirror hoặc hình hộp. Tệp nguồn được lưu riêng, hồ sơ có URL, hash, đơn vị và số đo từng mặt. Tệp CAD sử dụng là bản DXF mm sạch metadata, không còn lỗi audit.

Một bản CAD có thể phục vụ nhiều cấu hình, nhưng lần này chỉ tạo liên kết dòng giá tường minh cho hai mã nêu trên. Chưa tự xác nhận tất cả mã cùng họ có cùng đầu cực, tư thế cơ cấu, phụ kiện hoặc kích thước. `auto_select=false`, `exact_cad_match=false`; các số đo là bao hình CAD, không phải chứng nhận kích thước thân/lỗ gá để chế tạo.

Nguồn: [CAD iC60N được đính kèm theo A9F74150 trên ElectGo](https://electgo.com/product/se-a9f74150), liên kết tệp tải trực tiếp từ `download.schneider-electric.com`; [thông số A9F74150 trên Schneider](https://eshop.se.com/sg/ic60n-miniature-circuit-breaker-1p-50a-c-curve-a9f74150.html). [CAD LRD21 trên Nuova Elva](https://nuovaelva.it/store/en/shop/brands/TEL/items/LRD21), tệp từ kho `schneider_synd` của Distributor Data Solutions; [xác nhận LRD21 từ Schneider](https://www.se.com/in/en/product/LRD21/thermal-overload-relay-tesys-lrd-12-18-a-class-10a/).

[Ảnh kiểm tra 12 mặt](../schneider-full-faces-2026-10-21.png), [tệp chứng cứ từng mặt](../schneider-full-faces-2026-10-21.json).

## Đã chặn các mục lỗi/chưa đủ bằng chứng

- Cách ly 7 mặt chưa xác nhận hướng nhìn, gồm các bản nguồn/cụm chuyển nguồn và bản đo lường chưa xác định. Chuyển CAD khỏi cây thư mục sử dụng và giữ bản sao hồ sơ để đối chiếu.
- Cách ly mặt trước EZS400 4P bị thiếu chi tiết đầu cực. Mặt hợp lệ còn lại được giữ, cập nhật mặt mặc định sang mặt đó. Không tính mặt lỗi vào số mặt hiện có.
- Ẩn 3 mục RMU E01/E02/E03 (7 mặt) đã bị gán Schneider khi hồ sơ không có bằng chứng hãng. Thu hồi mục chứng cứ gán hãng, giữ hồ sơ nguồn cho lần xác minh sau. Quy tắc CatalogTB yêu cầu không gán ABB/Schneider cho các RMU này khi chưa xác minh.
- Chặn ID gốc và ID công khai của các mặt bị cách ly/giữ lại; đường dẫn cũ không còn trả tài sản CAD. Lọc cả chỉ mục cũ còn lưu trong bộ nhớ. Bộ lọc sức khỏe CAD trước đây dùng cho ABB/LS/CHINT nay áp dụng thêm Schneider.

Tổng cộng 15 tham chiếu mặt bị chặn: 7 chưa xác định, 1 lỗi nét và 7 thuộc ba mục RMU thiếu chứng cứ hãng. Không coi tất cả các mặt này là lỗi hình học; lý do giữ lại được lưu riêng.

## Bảng giá và thông số

Đã đọc lại trang PDF 44 (trang in 42) của [MasterPriceBook Schneider Việt Nam 07/2026](https://www.se.com/vn/vi/download/document/MasterPriceBook/) lưu trong dự án. Đối chiếu đúng dòng mã, dòng định mức và tiêu đề cột/số cực/điện áp:

- Chuẩn hóa 72 dòng iK60N/iC60N theo họ, cực, dòng, đặc tuyến C và khả năng cắt danh mục tại điện áp được ghi trong bảng.
- Sửa 36 mã iC60N bị ghi nhầm RCCB thành MCB. Không đổi số tiền, VAT hoặc mã dòng giá.
- Không gọi toàn bộ giá trị 6 kA trong bảng giá là Icu. Giá trị danh mục được ghi riêng theo điện áp; Icn/Icu và tiêu chuẩn của A9F74150 được giữ thành các trường riêng từ dữ liệu sản phẩm.
- Bổ sung số đo 2D ngang × cao theo từng mặt cho 232 mục/301 mặt đang hiển thị. Hai bộ CAD mới có đủ mặt khớp để lấy thêm bao hình W×H×D. Vị trí thường lắp và kiểu lắp chỉ hiện khi có thông tin phù hợp; không đưa ghi chú nội bộ/tài liệu kiểm tra lên giao diện.

[72 dòng đã đối chiếu](mcb-pricebook-corrections.json), [nhật ký thay đổi](changes.json).

## Kết quả xác minh và phần còn thiếu

- Hiện hiển thị **232 mục Schneider, 301 mặt CAD hợp lệ**; không còn nhãn mặt chưa xác định hoặc mặt lỗi đã biết trong danh sách này.
- Đọc lại 301 DXF: đều mm, không lỗi audit hoặc sửa chữa trong bộ nhớ; SVG khai báo tồn tại và đọc được. Kiểm tra cấu trúc không chứng nhận đúng toàn bộ chi tiết cơ khí của từng mã đặt hàng.
- Đã thử 60 trường hợp URL cũ của các mặt bị giữ lại: đều 404. Đọc qua dịch vụ 24 tài sản DXF/preview của 12 mặt mới: đạt.
- 53 bài kiểm tra backend đạt. API đã nạp bản cập nhật, health 200. FE hiện có đã hỗ trợ thông số theo mặt nên không cần thay đổi mã FE trong đợt này.
- **Vẫn còn 179 mục chỉ một mặt, 230 mục chưa có bộ sáu hướng cùng biến thể.** Các mục này không bị kết luận là hỏng chỉ vì thiếu góc; giữ trong hàng chờ bổ sung. Không bắt buộc mọi bản khoét/gá phải có sáu hướng như thân thiết bị.
- Còn 4.276 dòng bảng giá chưa có liên kết CAD tường minh. Đây là thiếu ánh xạ đã kiểm chứng, không phải khẳng định chắc chắn không có CAD liên quan.
- Bộ MCADPP0003369 tải từ trang LC1D09M7 đang ghi tên “Control Relay AC” và có bao mặt trước rộng 59,26 mm, khác thân contactor 45 mm: giữ trong `Schneider/NguonBenNgoai/MCADPP0003369-PENDING`, chưa công bố hoặc gán cho mã contactor.

[Kết quả kiểm chứng](verification.json), [kiểm kê sau cập nhật](after-audit/summary.json), [các mặt còn thiếu](after-audit/missing-views.csv), [dòng giá chưa liên kết](after-audit/pricebook-without-explicit-cad.csv), [mục còn cần xác minh nhận diện](after-audit/identity-review.csv).

## Bổ sung ngày 22/10 — tên hãng và GV2ME10

- Tên hãng hiển thị thống nhất **Schneider Electric**; bộ lọc cũ `Schneider` vẫn tương đương, kể cả snapshot cũ. FE loại tên trùng khi nhận dữ liệu cache.
- Bổ sung bộ MCADPD0003997, sáu mặt riêng cho GV2ME10, 3P, dải chỉnh định 4–6,3 A; liên kết đúng dòng bảng giá, không đổi giá. Đối chiếu các liên kết trên [Nuova Elva GV2ME10](https://nuovaelva.it/store/en/shop/brands/TEL/items/GV2ME10) và thông số trên [trang hãng](https://www.se.com/uk/en/product/GV2ME10/). Không lấy thông số GV2ME14 từ trang phát hiện ban đầu.
- Hình học gốc giữ nguyên tỷ lệ mm; tên mặt ngắn, có đo ngang × cao từng mặt. Sáu DXF xuất bản đều qua audit không lỗi/sửa chữa. CAD họ không tự xác nhận mọi cấu hình hay kích thước chế tạo.
- Tổng mới: **233 mục Schneider Electric / 307 mặt**, ba bộ CAD mới đầy đủ sáu hướng tính từ đầu đợt; vẫn còn 179 mục một mặt. Số liệu các mục phía trên là mốc trước lần bổ sung này.
- [Xác minh bộ mới và tên hãng](gv2me10-verification.json). FE commit `26a4e007`.

# Cập nhật đối chiếu giá và CAD — 22/10/2026

Đã áp dụng 723 liên kết mới vào 66 hồ sơ CAD đang hoạt động: ABB 405,
Schneider Electric 115, Mitsubishi Electric 203. Kiểm tra dữ liệu trả cho giao
diện xác nhận cả 723 mã đều có giá. Mã đặt hàng bằng chữ số của Mitsubishi
được nhận diện qua ID dòng giá đã đối chiếu. Không thay đổi số tiền trong bảng giá.

Đã nhập thêm 10 model INVT, mỗi model đủ 6 mặt độc lập, tổng cộng 60 DXF và
60 bản xem trước: GD20-2R2G-4, GD20-2R2G-S2, GD20-5R5G-4, GD20-015G-4,
GD20-030G-4, GD20-037G-4, GD20-045G-4, GD20-075G-4, GD20-090G-4,
GD20-110G-4. Nhãn mặt chỉ gồm trước, sau, bên trái, bên phải, trên, dưới.
Giữ riêng kiểu gá vít và mặt bích. Kích thước bao CAD giữ cả bộ gá, tay thao tác,
đầu nối nhô của nguồn gốc; không ép bằng kích thước thân danh nghĩa trong catalogue.
Dòng vào và dòng ra của biến tần được ghi riêng.

Nguồn INVT: [trang hãng](https://www.invt.com/products/gd20-series-vfd-drive-14),
[catalogue hãng](https://www.invt.com/uploads/file1/20251114/GD20%20Catalog%28EN%29-V1.1.pdf),
[bộ DWG/STEP do Ruselkom phân phối](https://novosibirsk.ruselkom.ru/chastotnye-preobrazovateli/chastotnye-preobrazovateli-invt/gd20-kompaktnyy-mnogofunktsionalnyy/).
Đã lưu cả ba gói EPLAN chính hãng để đối chiếu thêm.

Đã tải bộ 8 IGES chính hãng Hyundai HGM100/HGM125 (2P, 3P, 4P NRST/RSTN)
và catalogue 2026 từ [trang tải hiện hành của HD Hyundai Electric](https://www.hd-hyundaielectric.com/elect/en/customer/download.jsp?searchValue=HGM&code3=DT_0006).
Các bản chuyển đổi được giữ ngoài chỉ mục công khai; chưa tính vào CAD đã bổ sung.
Đã thử ba cách đọc trạng thái hình học IGES. Chi tiết đầu nối/tay thao tác và bao
hình của các bản chuyển đổi chưa thống nhất với cấu hình lắp chính xác; ghi trong
`Hyundai/NguonBenNgoai/HGM100-125/review.json`, không công bố ứng viên này.
Đã tải ba bộ DWG Mikro MX200A/MX180A/MX160A từ
[trang hãng Mikro](https://itmikro.com.my/mx200a-160a-voltage-relay/).
Nguồn ghi là mặt trước; bản MX200A đọc trên hình là MX200, cần đối chiếu biến thể
và bổ sung các mặt khác trước khi công bố như một bộ CAD thiết bị đầy đủ.

## Kiểm chứng

- 723/723 liên kết mới có giá trong dữ liệu giao diện: `customer-verification.json`.
- 1.770 mặt thuộc ABB, LS, CHINT, Schneider và INVT được kiểm tra kích thước,
  hash và loại trừ chú thích kích thước; không có bản đo nào phải gỡ ở bước cuối.
- 34 kiểm tra hồi quy và 21 kiểm tra thông tin/kích thước khách hàng chạy đạt;
  kiểm tra lặp sau sửa cuối cũng đạt.
- Hai API worker đã nạp lại; `/health` trả về 200.
- Đây là kiểm tra API tại máy chạy. Phép thử đường dẫn health bên ngoài trả 403;
  chưa xác minh phiên trình duyệt có đăng nhập trên website công khai.
- Hồ sơ sửa có bản sao trước cập nhật trong `before/`; overlay trước sửa được giữ
  trong `published-information.before.json`.

## Phần còn thiếu được giữ rõ ràng

`all-price-rows.csv` và `coverage-summary.json` đối chiếu toàn bộ 14.772 dòng của
18 hãng, không chỉ bốn hãng ban đầu. Trạng thái `needs_explicit_link_or_source`
nghĩa là cần ghép có căn cứ hoặc tìm thêm nguồn; không đồng nghĩa đã chứng minh
thiết bị không có CAD. Liên kết theo họ thiết bị cũng không chứng minh SKU đã
được duyệt điện hay mọi kiểu lắp đều dùng chung hình học.

Không ép ghép biến thể Shihlin chưa đủ bằng chứng kích thước, contactor Mitsubishi
khác tiếp điểm phụ, CVS400 có nhiều bản cơ khí hoặc LRD21 có thông số dòng mâu thuẫn.
Chi tiết nằm trong `held-links.json`. Bốn nguồn STEP INVT lỗi tạo hình chiếu
(GD20-018G-4, GD20-022G-4, GD20-0R4G-S2, GD20-0R7G-S2) chưa được đưa lên giao diện.
Không tạo mặt còn thiếu bằng cách sao, lật hay kéo tỷ lệ mặt đã có.

Các kho tải mới dung lượng lớn được giữ trên ổ D qua junction trong CatalogTB;
nguồn gốc và dữ liệu kiểm tra vẫn truy cập qua cây thư viện của dự án.

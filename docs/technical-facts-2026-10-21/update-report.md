# Điều chỉnh thông số hiển thị ABB, LS và CHINT

Phạm vi: 395 mục thư viện đang hiển thị (ABB 94, LS 264, CHINT 37). Không sửa hình học CAD hoặc đánh dấu các bộ thiếu mặt thành bộ hoàn chỉnh.

## Giao diện

Đã bỏ các câu hướng dẫn/ghi chú như “Dải mã tham khảo · kiểm tra điện áp và cấu hình khi chọn”, “Đối chiếu cấu hình”, “Bao hình”, “Giữ tư thế … STEP”, cùng các giá trị chưa xác nhận/để trống khỏi dữ liệu khách hàng và bộ lọc FE. Mã đặt hàng thật vẫn được giữ. Thông số theo phương án CAD được hiển thị theo mặt/phương án đang chọn, không áp cho các phương án khác.

## Dữ liệu được công bố

| Hãng | Mục đã rà soát | Có kích thước chính | Có kích thước CAD theo phương án | Có dòng định mức/dải dòng | Có vị trí thường lắp |
|---|---:|---:|---:|---:|---:|
| ABB | 94 | 0 | 8 | 24 | 86 |
| LS Electric | 264 | 133 | 0 | 128 | 224 |
| CHINT | 37 | 8 | 0 | 10 | 32 |

Kích thước CAD là bao kích thước đo trên hình học đã xác minh đơn vị/hash và cùng biến thể; không gọi đó là kích thước thân catalogue. Với bộ trục tay xoay thay đổi chiều dài hoặc bảng/cụm nhiều thiết bị, không tự công bố một kích thước thiết bị đơn. Các thông số thiếu hoặc mâu thuẫn được để ẩn. Vị trí thường lắp là gợi ý theo chức năng, không phải một vị trí bắt buộc do hãng chỉ định.

## Dòng cắt theo điện áp

- LS: 12 mã c-series được bổ sung các giá trị Icu theo từng mức điện áp từ tài liệu chính hãng trang PDF 8–9, đưa vào thông số và bảng theo từng mã. Ví dụ ABN103c: 18 kA tại 415/460 V AC; 22 kA tại 380 V AC; 35 kA tại 220/250 V AC. Không suy ra điện áp của dòng Icu không ghi điện áp trong bảng giá.
- CHINT NXM-160S/NXM-250S: Icu 36 kA tại 380/400/415 V AC theo bảng kỹ thuật trang PDF 27. Chỉ ghép đúng họ S và số cực; không chuyển giá trị từ F/H hoặc cực khác. Ics không được điền khi bảng tổng quát và bảng đặt hàng trong tài liệu chưa thống nhất.
- Khi một họ CAD dùng cho nhiều mã điện khác nhau, không đưa một giá trị chung vào phần thông số nếu các mã không thống nhất; giữ thông tin theo từng mã ở bảng sản phẩm. Không lấy Icu/Ics từ hình dạng CAD.

## Nguồn

- [LS Metasol MCCB/ELCB Technical Manual, PDF 8–9](https://www.ls-electric.com/upload/customer/download/1213/Metasol_MCCB-ELCB_Technical%20Manual_E.pdf)
- [CHINT NXM catalogue, PDF 27](https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/catalog/NXM-MCCB-Catalog.pdf)
- Hồ sơ nguồn ABB cho từng mặt/phương án có document ID, URL chính hãng và SHA256 trong unit_verification của hồ sơ CAD; chỉ dùng các cặp mặt có hash và bao hình khớp.
- Các giá trị còn lại lấy từ tham chiếu đúng hãng, họ/mã và số cực đã có trong thư viện; không gộp kích thước mâu thuẫn hoặc trộn AC/DC/tiếp điểm phụ.

## Kiểm tra và triển khai

35 bài kiểm tra backend đạt; kiểm tra FE xác nhận ghi chú bị ẩn nhưng kích thước, kiểu lắp, dòng cắt và mã đặt hàng còn hiển thị. Production build đạt. Đã kiểm tra payload của 395 mục và 16 mặt/phương án có kích thước riêng. FE đã đẩy commit cb858d01; trạng thái triển khai được ghi trong verification.json.

Chi tiết: [CSV thông số](technical-facts.csv), [dữ liệu khách hàng](customer-responses.json), [số liệu](summary.json), [kiểm tra](verification.json).

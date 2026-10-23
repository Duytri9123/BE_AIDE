# Kiểm kê và bổ sung CAD ABB, LS, CHINT, Schneider Electric — 22/10/2026

**Chưa phủ đủ catalog/bảng giá.** Phạm vi đã đối chiếu là 10.882 dòng trong các bảng giá hiện có của bốn hãng, toàn bộ hồ sơ CAD liên quan trong CatalogTB và dữ liệu hiển thị mới dựng từ nguồn. Không coi một CAD là một mã đặt hàng; một hình học có thể dùng cho nhiều mã khi họ, số cực, kiểu gá và đầu nối phù hợp.

## Tình trạng sau cập nhật

| Hãng | Mục CAD hiển thị | Mặt CAD | Mục đủ sáu hướng cùng biến thể | Mục còn một mặt | Dòng giá chưa liên kết CAD tường minh |
|---|---:|---:|---:|---:|---:|
| ABB | 98 | 268 | 4 | 4 | 4.099 / 4.446 |
| LS Electric | 270 | 1.045 | 117 | 61 | 138 / 517 |
| CHINT | 38 | 90 | 7 | 17 | 1.114 / 1.505 |
| Schneider Electric | 233 | 307 | 3 | 179 | 4.274 / 4.414 |
| Tổng | 639 | 1.710 | 131 | 261 | 9.625 / 10.882 |

“Chưa liên kết” là thiếu ánh xạ đã kiểm chứng với dòng giá, không phải khẳng định chắc chắn không có hình liên quan. 508 mục chưa có đủ sáu hướng của cùng biến thể; một số là bản khoét/gá nên không áp dụng yêu cầu sáu mặt thân thiết bị. Còn 137 mục cần đối chiếu nhận diện/cấu hình theo tiêu chí kiểm kê; không tự coi các ứng viên đó là mã đặt hàng đã xác minh.

## Đã bổ sung

- **ABB: 24 mặt / bốn bộ S200/S200M 1P–4P**, dùng các STEP chính hãng trong dịch vụ tải tài liệu ABB, giữ toàn bộ mô hình gốc. Liên kết 36 dòng giá S201M/S202M/S203M/S204M, 6–63 A. Không ghép sang S200 80/100 A hoặc biến thể có cực N. Các liên kết này là tham chiếu hình học cùng họ, không phải chứng nhận cấu hình điện của từng mã.
- **LS: 36 mặt / sáu bộ LA63Hd**: 1P, 1P+N, 2P, 3P, 3P+N, 4P. Giữ riêng cực N và các hướng. Bảng giá hiện chưa có dòng LA63Hd được xác minh, nên không ghép sang LA63H/N/L hoặc LA125H; giá và thông số điện chưa biết được để trống.
- **CHINT: 12 mặt / KG316T và NKG1**. Đối chiếu màn hình, chữ, cọc đấu dây và kiểu gá với bản vẽ kích thước của hãng. KG316T dùng kiểu gá vít, đối chiếu dòng AC220V/mã 309010; không ghép sang KG316T-D gá DIN. NKG1 chưa có dòng giá hiện tại được xác minh. Lưu trữ mẫu KG316T cũ chỉ một mặt, không có nhãn model đã xác minh, ngoài thư viện đang hiển thị; bộ sáu mặt chính hãng thay thế mẫu đó.
- **Schneider Electric: thêm liên kết LRD14 vào bộ MCADPD0004675 đã có**, không nhân đôi hình CAD. Đã tải và so SHA256: cả sáu file trên trang LRD14 giống từng byte với nguồn LRD21. Giữ riêng LRD14 7–10 A và LRD21 12–18 A, class 10A.

Tổng nhập mới **72 mặt**, lưu trữ ngoài hiển thị một mặt cũ: số mặt hiển thị tăng ròng 71. Thêm 37 liên kết dòng giá trước đây chưa có CAD tường minh; chuyển KG316T từ tham chiếu một mặt sang bộ sáu mặt. Không sửa số tiền trong bảng giá.

## Nguồn đã tìm rộng nhưng chưa công bố

24 bộ nguồn CHINT được lưu trong `Chint/NguonBenNgoai`, có hash và trạng thái chờ kiểm tra:

- NXB-63 1P–4P: tên file tải và nhãn NXB-63H trong một số tờ không thống nhất; tờ 1P thiếu nhãn model và có khác biệt giữa chú kích thước/bao hình. Không chuyển thẳng sang các dòng giá NXB-63.
- NB1-63H 1P/2P/4P: IGES 1P nạp ra bao toàn bộ khoảng 431 × 525 × 1.116 mm, không phù hợp một MCB đơn. Chưa xác định cấu trúc/đơn vị/tư thế, không cắt bỏ hoặc đổi tỷ lệ tùy ý.
- NDK 17 mức VA: đã tải STEP và catalog hãng, tạo các hình chiếu để rà soát. Tư thế mô hình khác nhau; NDK-100 bị nghiêng so với trục xuất. Chưa công bố khi mặt trước, trên/dưới và mặt gá chưa được xác nhận riêng từng bộ. NDK-2500 còn cần tài liệu biến thể vì không có trong bảng tiêu chuẩn PDF đã tải.

[Nhật ký nguồn và trạng thái](source-search.json). Nguồn ngoài chỉ được dùng sau khi nhập thành hồ sơ CatalogTB đã kiểm tra; không dùng làm fallback trực tiếp khi bố trí.

## Kiểm chứng

- Kiểm kê nguồn sau cập nhật: 1.716 DXF, không lỗi đọc, không lỗi audit, không sửa chữa trong bộ nhớ, không mặt đang hiển thị bị thiếu file/preview hoặc chưa xác định hướng.
- 1.644 DXF cũ khớp SHA256 với lần đọc kiểm tra toàn bộ đầu đợt; 72 DXF mới được đọc/audit mới. Tất cả preview khai báo được kiểm tra tồn tại và XML hợp lệ.
- Cả 1.710 mặt đang hiển thị có số đo ngang × cao lấy từ hình học CAD theo đơn vị mm. Bao hình CAD không thay cho khoảng đấu dây, lỗ gá hay kích thước chế tạo được chứng nhận.
- Kiểm tra 144 lượt tải DXF/preview của các mặt mới; bốn lượt truy cập ID/URL cũ của mẫu KG316T lưu trữ bị chặn. 38 kiểm thử đạt. API được nạp lại sau cập nhật dữ liệu.

[Kết quả xác minh](verification.json) · [Kiểm kê trước](../four-brands-audit-2026-10-22/summary.json) · [Kiểm kê sau](../four-brands-audit-2026-10-22-after/summary.json) · [Các mặt còn thiếu](../four-brands-audit-2026-10-22-after/missing-views.csv) · [Dòng giá chưa liên kết](../four-brands-audit-2026-10-22-after/pricebook-without-explicit-cad.csv).

Ảnh rà soát các bộ mới: [ABB](../four-brands-abb-additions-2026-10-22.png), [LS](../four-brands-ls-additions-2026-10-22.png), [CHINT](../four-brands-chint-additions-2026-10-22.png).

## Nguồn đối chiếu chính

- [ABB Connect — tài liệu CAD liên kết theo sản phẩm](https://www.abbconnect.nl/Details/Index.aspx/2CDS251001R0061?ShowBorder=True&country=nl&languageCode=en); tài liệu STEP 9AKK106930A4834–A4837 ghi rõ S200/S200M và các cấu hình cực.
- [LS ELECTRIC Download Center](https://www.ls-electric.com/ko/download/); hồ sơ LA63Hd 421284, file 55466–55471. Lưu phản hồi danh sách file và URL nguồn trong hồ sơ.
- [CHINT KG316T](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/kg316t.html), [NKG1](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/nkg1.html), [NDK](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/ndk.html), [NXB-63](https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html), [NB1-63H](https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nb1-63h.html).
- [Nuova Elva — CAD LRD14](https://nuovaelva.it/store/en/shop/brands/TEL/items/LRD14), [Schneider Electric — thông số LRD14](https://www.se.com/uk/en/product/LRD14/).

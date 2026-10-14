# Đối chiếu toàn bộ thư viện thiết bị

Cập nhật 14/10/2026: 837 thiết bị; 103 thiết bị có lựa chọn giá theo mã/họ thiết bị và cấu hình, tăng từ 90 sau khi sửa dữ liệu và đối chiếu. 8764 dòng giá được công bố; đủ 32/32 hãng trong phạm vi bảng giá có ít nhất một dòng. Đây không phải xác nhận toàn bộ CAD đã có mã đặt hàng hoặc hình vẽ được phê duyệt.

Bổ sung ròng 421 dòng PDF và 2.619 dòng giá nhà bán hàng so với lần cập nhật trước. Các bản Fuji/IDEC là năm 2025; các bản Mikro/Shihlin/Vinakip là 2026. Nguồn web có thời điểm kiểm tra và ghi chú cần xác nhận VAT/tồn kho. Không đổi giá tham khảo thành giá hãng.

| Hãng | Dòng giá | CAD trong thư viện theo nhãn hãng | CAD có lựa chọn giá |
| --- | ---: | ---: | ---: |
| Schneider Electric | 135 | 241 | 7 |
| ABB | 726 | 80 | 33 |
| Siemens | 127 | 0 | 0 |
| Hager | 200 | 0 | 0 |
| Legrand | 103 | 0 | 0 |
| BTB Electric | 38 | 0 | 0 |
| Mitsubishi Electric | 3066 | 39 | 26 |
| Fuji Electric | 152 | 0 | 0 |
| LS Electric | 697 | 134 | 12 |
| Shihlin | 246 | 20 | 10 |
| CHINT | 1729 | 28 | 4 |
| Andeli | 1 | 0 | 0 |
| Sino - Vanlock | 178 | 0 | 0 |
| Vinakip | 26 | 0 | 0 |
| Omron | 10 | 2 | 1 |
| Delta | 49 | 0 | 0 |
| Yaskawa | 6 | 0 | 0 |
| Danfoss | 6 | 0 | 0 |
| INVT | 102 | 0 | 0 |
| IDEC | 183 | 0 | 0 |
| Hanyoung Nux | 214 | 17 | 0 |
| Samwha | 45 | 9 | 0 |
| TDK / EPCOS | 29 | 0 | 0 |
| Shizuki | 42 | 0 | 0 |
| Nuintek | 135 | 20 | 0 |
| Mikro | 214 | 8 | 5 |
| SK | 3 | 0 | 0 |
| Ducati Energia | 2 | 0 | 0 |
| Selec | 28 | 0 | 0 |
| Delixi | 172 | 0 | 0 |
| Morele | 14 | 2 | 0 |
| EMIC | 86 | 13 | 5 |

## Phần còn thiếu

734/837 CAD chưa có lựa chọn giá phù hợp. Trong đó: 280 CAD đã xác định hãng nhưng thiếu mã/cấu hình hoặc nguồn giá đúng mã; 251 CAD chỉ xác định thư viện nguồn; 77 chưa rõ hãng; 15 nhãn hãng ứng viên; 111 phụ kiện phổ thông không áp hãng. Các mã ứng viên dựa kích thước của tụ Nuintek/Samwha chưa được đưa thành mã xác nhận. Không tự thay NX201A/MK201A bằng N201/R201.

Andeli mới có 1 dòng, Ducati Energia 2, SK 3, Danfoss 6, Yaskawa 6; cần bổ sung thêm danh mục đúng mã khi có nguồn. Nguồn PLE/Makel chỉ rà trang hãng đầu tiên, không tuyên bố đã lấy toàn bộ kho nhà bán hàng.

Phát hiện nguồn Sino dùng SC45N/C3006 cho cả 3P và 4P với hai giá khác nhau: loại cả hai khỏi dữ liệu công bố, chưa tự sửa mã trong tài liệu nguồn.

## Liên kết dùng chung

Bảng giá, thư viện CAD và bóc tách dùng chung published_rows. Một CAD có thể có nhiều lựa chọn giá; đối chiếu hãng, loại, mã/họ thiết bị và số cực. Mã thân ABB hoặc họ BM/MX/PFR được đưa thành lựa chọn, không tự chốt điện áp, dòng điện hay mã đặt hàng. Server xác minh giá theo ID dòng công bố khi người dùng chọn.

## Nguồn kiểm tra

- [PDF Shihlin 2026](https://www.saigonelectric.vn/images/prices/SHIHLIN_01.02.2026.2.pdf)
- [PDF Mikro 2026](https://www.saigonelectric.vn/images/prices/MIKRO_15-01-2026.2.pdf)
- [PDF Fuji 2025](https://www.saigonelectric.vn/images/prices/Fuji_2025_MNE.2.pdf)
- [PDF IDEC 2025](https://www.saigonelectric.vn/images/prices/IDEC_04.2025_R4.2.pdf)
- [Vinakip 01/07/2026, trang 18](https://kimquang.vn/wp-content/uploads/2022/07/bang-gia-cau-dao-hop-vinakip.pdf)
- [PLE: nguồn danh mục hãng](https://www.ple.vn/manufacturer/delixi/by%2Cmf_name/results%2C1-180.html?keyword=&lang=vi&language=vi-VN)
- [Makel Hager](https://www.makel.vn/thiet-bi-dong-cat-chong-dong-ro?brand=2), [Legrand](https://www.makel.vn/thiet-bi-dong-cat-chong-dong-ro?brand=3), [Siemens](https://www.makel.vn/thiet-bi-dong-cat-chong-dong-ro?brand=29)
- [Sino-Vanlock](https://thietbidiennuochanoi.vn/pages/bang-gia-aptomat-sino-vanlock)
- [SK](https://dienhoaphu.vn/danh-muc-san-pham/thiet-bi-dien-cong-nghiep/tu-bu-bo-dieu-khien-tu-bu-cuon-khang/bo-dieu-khien-tu-bu/sk/)
- [Danfoss](https://eriko.com.vn/san-pham/3332-bang-gia-cam-bien-do-ap-suat.html)
- [Andeli](https://vanvh.com/den-bao-pha-cac-loai/den-bao-do-vang-xanh-phi-22-andeli-andeli-ad16-22ds)
- [Morele](https://hanhdungelectric.com.vn/quat-lam-mat-huong-truc-morele)
- [Delta](https://codienhaiau.com/brand/delta/)

Kiểm tra hồi quy: 39 tests về parser giá, liên kết CAD, bóc tách/báo giá và nhận diện hãng.

Cập nhật tiếp: thêm 73 dòng ABB 2026 (contactor 1SFL và rơ le nhiệt trang 117), gắn họ S200/SH200 theo trang 141–143; giữ dải chỉnh định rơ le thay vì gán thành dòng cố định. Xác nhận 4 cực cho MC-9a/4, MC-12a/4, MC-18a/4 theo [tài liệu LS, trang 14](https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf). Không đổi các MC-40 cũ thành MC-40a hoặc lấy điện áp cuộn hút theo suy đoán.

## Rà lại 293 CAD đã rõ hãng, ngày 14/10/2026

Đây là phân loại sau sửa, không còn gộp toàn bộ thành thiếu báo giá. Có thêm 13 CAD dùng được giá đã có sẵn; không bổ sung hay thay đổi giá bán trong đợt này. Tổng có lựa chọn giá 103/837; còn 280 CAD đã xác định hãng chưa có lựa chọn phù hợp.

| Lý do hiện tại | CAD | Ý nghĩa |
| --- | ---: | --- |
| Chưa có mã/họ thiết bị đủ căn cứ | 55 | Hãng đã xác định, nhưng mã chỉ là ứng viên theo kích thước hoặc chưa đọc được. |
| Không thấy mã trong dữ liệu giá đã công bố | 137 | Không kết luận thị trường không có giá; cần thêm nguồn đúng mã, mã cũ hoặc mã đầy đủ. |
| Có chuỗi mã liên quan nhưng chưa khớp | 52 | Có thể khác thế hệ, khác loại, thiếu số cực/thông số hoặc chỉ là giá phụ kiện cho thiết bị. Không lấy giá theo chuỗi con. |
| Chưa có giá dưới nhãn hãng hiện tại | 36 | Có hãng ngoài 32 hãng bảng giá và hai nhãn Schneider RM6 kèm ghi chú; giá cùng hãng của thiết bị khác không thay thế được. |

Đã sửa: BV-D nhập từ sheet “MCB China” được phân loại đúng RCCB; S-T10/12/20/21/25/35/50 có 3 cực theo tài liệu hãng; XJ3-G là rơ le bảo vệ pha; Omron-S8FS-C05024J được bỏ dấu nối giữa tên hãng và mã; họ NP2-EA và iC60N thành lựa chọn có kiểm soát. Đối chiếu 1P+N yêu cầu đúng ký hiệu trung tính, không coi tương đương 1P. Giữ nguyên giá bán và ID nguồn.

Ví dụ phải giữ chưa khớp: ABB A2 trong CAD là 1P nhưng các dòng A2 đang có là 2P/3P/4P; ZCT120 khác ZCT120S; MC-40 khác MC-40a; bảng giá phụ kiện “SHT for ABN100c” không phải giá MCCB ABN100; MCCB Mitsubishi NF125-CV 4P không được lấy giá 2P/3P.

Chi tiết từng CAD: [library-verified-price-gaps.json](library-verified-price-gaps.json). Tái lập bằng `venv/Scripts/python.exe scripts/audit_library_price_gaps.py`. “related_code_only” chỉ là gợi ý tra cứu, không phải xác nhận giá đúng hoặc phê duyệt CAD.

Nguồn kiểm tra phân loại: [BV-D](https://www.mitsubishielectric.com/fa/sg_en/products/faspec/detail.page?category=ex&formNm=RCCB_RCBO_BV-D_4885&id=spec&kisyu=%2Flvcb&lang=2), [S-T](https://www.mitsubishielectric.com/dl/fa/document/catalog/lvsw/sh020011eng/SH%28NA%29020011ENG-A.pdf), [XJ3-G](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/xj3.html), [S8FS-C](https://www.ia.omron.com/products/family/3460/lineup.html), [NP2](https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-Push-button-Catalog.pdf), [iC60N](https://eshop.se.com/sg/ic60n-miniature-circuit-breaker-3p-2a-c-curve-a9f74302.html).

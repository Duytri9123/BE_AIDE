# Đối chiếu toàn bộ thư viện thiết bị

Cập nhật 14/10/2026: 837 thiết bị; 73 thiết bị có lựa chọn giá theo mã/họ thiết bị và cấu hình, tăng từ 49. 8691 dòng giá được công bố; đủ 32/32 hãng trong phạm vi bảng giá có ít nhất một dòng. Đây không phải xác nhận toàn bộ CAD đã có mã đặt hàng hoặc hình vẽ được phê duyệt.

Bổ sung ròng 348 dòng PDF và 2.619 dòng giá nhà bán hàng so với lần cập nhật trước. Các bản Fuji/IDEC là năm 2025; các bản Mikro/Shihlin/Vinakip là 2026. Nguồn web có thời điểm kiểm tra và ghi chú cần xác nhận VAT/tồn kho. Không đổi giá tham khảo thành giá hãng.

| Hãng | Dòng giá | CAD trong thư viện theo nhãn hãng | CAD có lựa chọn giá |
| --- | ---: | ---: | ---: |
| Schneider Electric | 135 | 241 | 4 |
| ABB | 653 | 80 | 17 |
| Siemens | 127 | 0 | 0 |
| Hager | 200 | 0 | 0 |
| Legrand | 103 | 0 | 0 |
| BTB Electric | 38 | 0 | 0 |
| Mitsubishi Electric | 3066 | 39 | 20 |
| Fuji Electric | 152 | 0 | 0 |
| LS Electric | 697 | 134 | 11 |
| Shihlin | 246 | 20 | 10 |
| CHINT | 1729 | 28 | 1 |
| Andeli | 1 | 0 | 0 |
| Sino - Vanlock | 178 | 0 | 0 |
| Vinakip | 26 | 0 | 0 |
| Omron | 10 | 2 | 0 |
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

764/837 CAD chưa có lựa chọn giá phù hợp. Trong đó: 310 CAD đã xác định hãng nhưng thiếu mã/cấu hình hoặc nguồn giá đúng mã; 251 CAD chỉ xác định thư viện nguồn; 77 chưa rõ hãng; 15 nhãn hãng ứng viên; 111 phụ kiện phổ thông không áp hãng. Các mã ứng viên dựa kích thước của tụ Nuintek/Samwha chưa được đưa thành mã xác nhận. Không tự thay NX201A/MK201A bằng N201/R201.

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

Kiểm tra hồi quy: 32 tests về parser giá, liên kết CAD, bóc tách/báo giá và nhận diện hãng.

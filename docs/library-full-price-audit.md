# Đối chiếu toàn bộ thư viện thiết bị

## Tìm mã cho nhóm 251 CAD nguồn — cập nhật mới nhất 14/10/2026

Đã tìm tài liệu hãng và bổ sung mã/dòng hoặc nhóm mã cho **95/251 CAD nguồn**: CHINT NXB-63, NXM-1600S và NZ7-125; LS BKN, MT-12/63, MC-185a/265a/500a và một số MCCB có hậu tố c rõ ràng; Schneider LC1D/LC1E/LC1F, EZC và Altivar 212/320/630. Nhận diện này dựa trên tên block nguồn đối chiếu tài liệu hãng, có ràng buộc checksum thư viện và từng DXF; không phải đọc logo trực tiếp, xác nhận mọi SKU hay phê duyệt hình học. Vẫn giữ auto_select=false và needs_review=true.

**59 CAD trong nhóm này đã có lựa chọn giá**. Bổ sung **98 dòng giá biến tần Schneider 07/2026 đã gồm VAT** từ 4 trang PDF được xem và kiểm tra cột: ATV320 Book/Compact, ATV212 IP21/IP55 và ATV630 có giá số. Không nhập các dòng ATV630C11 trở lên ghi “Contact for price”, không đổi hậu tố B/C, H/W hoặc lấy giá cùng công suất khác thân.

Nhóm nguồn còn **156 CAD cần xác minh thêm**: 51 nhãn/mã riêng chưa tìm đủ chứng cứ; 54 nhãn dùng chung/khung; 28 nhãn lỗ khoét/lắp đặt cần đối chiếu hình; 15 nhãn HCC/HCN chưa rõ ý nghĩa; 8 nhóm CAD cần kiểm tra từng thành viên. Đây là danh sách công việc còn lại, không phải toàn bộ đã xác minh xong. Không tự đổi LC1D185 thành LC1F185, ABS103 thành ABS103c, NS400_600 thành NS400/630 hoặc lấy mã mới thay bản vẽ đời cũ.

Hiện có **216/837 CAD có lựa chọn giá**, gồm **213/684 CAD ưu tiên bóc tách**, còn **471 CAD ưu tiên chưa có lựa chọn**; 153 cầu đấu/phụ kiện vẫn không bắt buộc giá chính xác. Tổng **9.476 dòng giá**. Kiểm tra đủ 837 CAD/1.448 mặt vẽ: không có lỗi cấu trúc; **70 kiểm tra đạt**. [Danh sách 251 CAD và nguồn đối chiếu](library-source-model-research.md), [báo cáo theo thư mục](library-folder-price-audit.md).

Nguồn chính: [LS Metasol](https://www.ls-electric.com/upload/customer/download/4d8b99a1-c93d-4cd3-807b-1382f0c39384/Metasol_MS_E_180903.pdf), [CHINT NXB-63](https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html), [Schneider LC1E25–38](https://www.se.com/us/en/download/document/EAV78697/), [Schneider nhóm Altivar630](https://www.se.com/us/en/faqs/FA302753/), [Master Pricebook](https://www.se.com/vn/vi/download/document/MasterPriceBook/).

Các mục dưới đây ghi lịch sử các lượt trước; dùng số liệu ở mục mới nhất phía trên.

## Rà đủ các mục và ưu tiên thiết bị bóc tách — cập nhật tiếp 14/10/2026

Đã rà dữ liệu của **26/26 thư mục, 837 CAD và 1.448 mặt vẽ**; đối chiếu web theo dòng/nhóm thiết bị. Đã xem tổng quan thêm **95 hình chiếu của 55 thiết bị ưu tiên chưa rõ hãng** cùng chữ DXF đã trích xuất; chưa có căn cứ đủ chắc để xác nhận thêm hãng từ các hình này. Việc rà dữ liệu/nguồn và xem tổng quan không phải phê duyệt kỹ thuật, kích thước hay mọi mã đặt hàng.

Theo yêu cầu người dùng, **153 cầu đấu/phụ kiện không bắt buộc khớp mã/giá chính xác**. Còn **684 CAD thiết bị cần đối chiếu giá**: **154 có lựa chọn giá, 530 chưa có lựa chọn phù hợp**. Tổng thư viện có 157 CAD có giá nếu tính thêm 3 phụ kiện đã có dữ liệu từ trước. Các phụ kiện được miễn yêu cầu không được tính thành thiết bị đã khớp giá.

Đợt này bổ sung **198 dòng giá**: 167 Schneider từ Master Pricebook 07/2026 chính hãng, 28 cấu hình ATS OSEMCO từ bảng ETINCO 15/03/2026 và 3 quạt Leipole từ bảng DGE 01/2026. Tổng công bố **9.378 dòng giá / 35 hãng**. Không thay giá/ID cũ. Schneider đã gồm VAT; ATS và quạt chưa VAT.

- Schneider tăng 13 CAD có lựa chọn giá: C120 1–4P, iIDK 2P/4P, CVS 3P/4P và LC1E. Giữ 220VAC và 24VDC thành các lựa chọn riêng, chưa tự chọn cuộn hút. CVS100BS không liên kết với CAD CVS100B/F/N. Nhóm in thành CVS639F trong PDF bị bỏ khỏi nhập, không tự sửa thành CVS630F hoặc gán nhầm sang CVS400F. Các LC1E có dấu * yêu cầu hỏi giá hiện tại chưa được nhập.
- ATS OSS-612-PC 4P 1250A đã có lựa chọn 70.150.000 đồng; không dùng giá 3P 56.500.000 đồng.
- 3 quạt Leipole đã có giá; sửa ánh xạ loại “Quạt lọc gió tủ điện” với nhóm FAN, giữ quạt kèm lọc khác miệng gió rời.
- Chẩn đoán Mitsubishi/LS cùng mã nhưng thiếu số cực được sửa thành “khác số cực”. PM710 được ghi rõ hãng đã ngừng thương mại tại châu Á–Thái Bình Dương từ 30/04/2015; không dùng giá PM51xx thay tự động.

530 trường hợp thiết bị ưu tiên còn lại: 251 hãng theo thư viện nguồn; 55 chưa rõ hãng; 1 hãng ứng viên; 54 thiếu mã; 119 thiếu giá đúng mã/loại; 32 thiếu giá theo hãng; 13 khác số cực; 2 A9D thiếu mã đầy đủ; 1 chưa khớp cấu hình; 1 biến áp thiếu cấu hình; 1 PM710 ngừng thương mại. [Từng CAD trong từng thư mục](library-folder-price-audit.md), [kết quả phân loại](library-classified-price-review.md).

66 kiểm tra đạt. Nguồn: [Schneider Master Pricebook](https://www.se.com/vn/vi/download/document/MasterPriceBook/), [ETINCO ATS](https://etinco.vn/wp-content/uploads/2025/05/bang-gia-bo-chuyen-nguon-ats-osemco-osung.pdf), [DGE Leipole](https://dge.vn/uploads/bao-gia/435736_20260114_122258.pdf), [PM710 ngừng thương mại](https://www.se.com/uk/en/faqs/FA264122/).

Các số liệu bên dưới là lịch sử trước lượt rà này.

## Kết quả hiện tại — bổ sung giá theo thư mục ngày 14/10/2026

Đã bổ sung ròng **416 dòng giá**, tổng **9.180 dòng** trong phạm vi 33 hãng có dữ liệu công bố. Giữ toàn bộ ID và giá cũ; thêm MITEX vào danh sách hãng có giá.

- **ABB: +355 dòng** theo bảng giá hãng Việt Nam 2026: Tmax XT1–XT4, FH/F200, DS201L và VE5. Thư mục ABB có 46/79 CAD có lựa chọn giá, tăng 13. Số cực được đọc theo cột 3P/4P trong PDF; giữ riêng cực N 50%/100%, bộ trip, dòng rò và mã đặt hàng.
- **MITEX: +60 cấu hình** từ giá bán công khai PLE, gồm 20 BD01. Giữ tỷ số dòng, cấp chính xác, VA, số vòng và cửa sổ; VAT/tồn kho cần xác nhận. Thư mục Biến dòng tăng từ 7 lên 8/43 CAD có lựa chọn giá.
- **Mikro: +1 dòng NX201A-240A**, giá bán nhà cung cấp 1.461.600 đồng. Không thay bằng N201/R201 và không tự xác nhận CAD đang có hai mã ứng viên NX201A/MK201A.

Rà lại toàn bộ **837 CAD và 1.448 mặt vẽ**: **140 CAD có lựa chọn giá**, tăng 14; **697 chưa có lựa chọn**. Không có lỗi cấu trúc đường dẫn/file/SVG trong kiểm tra này. Trong 697: 246 đã xác định hãng nhưng còn thiếu mã/giá/cấu hình, 251 theo thư viện nguồn, 75 chưa rõ hãng, 14 hãng ứng viên, 111 phụ kiện phổ thông.

Đã đối chiếu web thư mục ABB và Biến dòng; đang tiếp tục Bộ điều khiển. Các thư mục khác được ghi rõ chưa hoàn tất rà web, không coi việc kiểm tra tự động toàn bộ 837 CAD là đã xác nhận kỹ thuật từng bản vẽ. [Báo cáo từng thư mục, từng CAD và nguồn web](library-folder-price-audit.md), [phân loại kết quả toàn bộ CAD](library-classified-price-review.md).

58 kiểm tra đạt. Nguồn: [ABB Việt Nam 2026](https://library.e.abb.com/public/8fa0d161aec14871ae110caa57108c49/9AKK108472A7059_vi_B_EL%20Vietnam%20Master%20price%20list%202026%20%28VIE%29.pdf), [MITEX tại PLE](https://www.ple.vn/manufacturer/mitex/by,product_name.html?lang=vi&language=vi-VN), [NX201A hãng Mikro](https://itmikro.com.my/nx201a-earth-fault-relay/), [giá NX201A tại Hải Âu](https://codienhaiau.com/product/ro-le-bao-ve-cham-dat-mikro-nx201a-240a-0-1-2a/).

## Lịch sử các đợt trước — số liệu bên dưới giữ theo thời điểm đó

## Rà chữ bên trong toàn bộ DXF và sửa dữ liệu điều khiển

Đã đọc đủ 837 CAD và 1.448 file DXF, gồm TEXT/MTEXT, thuộc tính INSERT và chữ trong block lồng nhau. Không có lỗi trích xuất. Đây là rà dữ liệu chữ, chưa phải đọc bằng mắt mọi logo được vẽ bằng đường nét. [Bằng chứng chữ và SHA256 từng mặt](library-dxf-identity-audit.json).

- Thêm xác nhận IDEC từ nhãn chữ ở mặt bên; SW0.1 không được biến thành mã đặt hàng.
- Thêm xác nhận nhãn RISESUN và mã RT18-32 từ chữ trong CAD; chưa có nguồn giá của RISESUN, không lấy giá RT18-32 của hãng khác.
- Xác nhận DIN310 là rơ le dòng rò Mikro theo manual hãng, sửa tên/loại đang bị ghi thành giám sát pha. Dòng giá DIN310-230A được sửa điện áp phụ trợ 230V AC, loại bỏ giá trị sai In=230A; giá và ID không thay đổi.
- LS UA-1 được sửa từ CONTACTOR thành AUX_CONTACT. Mitsubishi BH-DN được ghi rõ 1P+N theo bảng thông số hãng. Schneider LC1D khớp mã thân cho nhóm CAD chung 9–18 và 25–38; LC1D098/128 là 4P, không đưa vào CAD 3P. Điện áp cuộn hút chưa được chọn tự động.

Tăng thêm 5 CAD có lựa chọn giá: tổng 126/837, còn 711. Hãng xác nhận 386, chưa rõ 75, ứng viên 14, theo thư viện nguồn 251, phụ kiện phổ thông 111. Trong 711: 151 chưa có giá đúng mã/loại; 55 chưa xác nhận mã; 37 chưa có giá theo nhãn hãng; 7 khác số cực; 7 chưa khớp cấu hình; 2 A9D thiếu mã đầy đủ; 1 biến áp thiếu cấu hình; cùng các nhóm hãng nguồn/ứng viên/chưa rõ/phụ kiện nêu trên.

Toàn bộ 251 CAD theo thư viện nguồn không có TEXT/MTEXT/thuộc tính chữ nhận diện trong các DXF kiểm tra. Tên block có mã gợi ý vẫn được giữ, nhưng không xem đó là chữ trên thiết bị hoặc tự xác nhận mã đặt hàng. Các logo dạng đường nét cần đối chiếu hình hoặc bản vẽ hãng riêng.

Kiểm thử: 53 kiểm tra đạt, gồm trích xuất block lồng nhau, ngăn vòng lặp block, giữ đúng số cực và không tự chọn điện áp cuộn hút. [Manual DIN310 của Mikro](https://itmikro.com.my/wp-content/uploads/2020/08/din310_man-1.pdf), [BH-DN của Mitsubishi](https://www.mitsubishielectric.com/fa/sg_en/products/faspec/detail.page?category=ex&formNm=MCB_BH-DN_4892&id=spec&kisyu=%2Flvcb&lang=2), [UA-1 của LS](https://gics.ls-electric.com/knowledgeBase/user/detail.do?baseId=170).

## Sửa đối chiếu mã khung và phân loại ngày 14/10/2026 (đợt tiếp theo)

Đợt trước sửa metadata của 70 dòng LS TD/TS và 16 dòng Schneider EZC, giữ nguyên ID và giá. Khớp theo mã khung đã được đối chiếu, loại thiết bị và số cực; hậu tố N/H/L, bộ trip và dòng điện vẫn phải được chọn. Không nhận TS1000 là TS100. Đợt đó thêm 18 CAD có lựa chọn giá (LS +10, Schneider +8); sau đợt đọc chữ DXF ở trên, tổng là 126, còn 711.

- ABB A2 · 1P: đã có giá A2 nhưng dữ liệu hiện là 2P/3P/4P; báo rõ khác số cực.
- Transformer CHINT: đã phân loại biến áp điều khiển, thiếu mã, VA và điện áp sơ/thứ cấp. NDK là dòng tham khảo có tài liệu, chưa gán thành mã của CAD từ hình dạng.
- Schneider A9D: đã nhận diện hãng và tiền tố, còn thiếu mã đầy đủ và xác nhận cấu hình chống rò; giữ nhãn CAD riêng.

[Bảng phân loại từng thiết bị trong toàn bộ 837 CAD](library-classified-price-review.md) đã cập nhật theo 711 trường hợp còn thiếu ở đợt đọc chữ DXF.

Nguồn đối chiếu: [LS Susol MCCB](https://www.ls-electric.com/ko/cat/%5BSusol%20MCCB%5D_Catalog_EN_202006.pdf), [Schneider EZC100H1015 1P](https://www.se.com/ph/en/product/EZC100H1015/circuit-breaker-easypact-ezc100h-tmd-15-a-1-pole-1d/), [Schneider EZC400H4320N 4P](https://www.se.com/in/en/product/EZC400H4320N/circuit-breaker-easypact-ezc400h-tmd-320-a-4-poles-3d/), [CHINT NDK](https://www.chintglobal.com/in/en/products/low-voltage/iec/industrial-control/ndk.html).

Cập nhật 14/10/2026: 837 thiết bị; 126 thiết bị có lựa chọn giá theo mã/họ thiết bị và cấu hình, tăng từ 121 sau khi sửa dữ liệu và đối chiếu. 8764 dòng giá được công bố; đủ 32/32 hãng trong phạm vi bảng giá có ít nhất một dòng. Đây không phải xác nhận toàn bộ CAD đã có mã đặt hàng hoặc hình vẽ được phê duyệt.

Bổ sung ròng 421 dòng PDF và 2.619 dòng giá nhà bán hàng so với lần cập nhật trước. Các bản Fuji/IDEC là năm 2025; các bản Mikro/Shihlin/Vinakip là 2026. Nguồn web có thời điểm kiểm tra và ghi chú cần xác nhận VAT/tồn kho. Không đổi giá tham khảo thành giá hãng.

| Hãng | Dòng giá | CAD trong thư viện theo nhãn hãng | CAD có lựa chọn giá |
| --- | ---: | ---: | ---: |
| Schneider Electric | 135 | 241 | 17 |
| ABB | 726 | 80 | 33 |
| Siemens | 127 | 0 | 0 |
| Hager | 200 | 0 | 0 |
| Legrand | 103 | 0 | 0 |
| BTB Electric | 38 | 0 | 0 |
| Mitsubishi Electric | 3066 | 39 | 27 |
| Fuji Electric | 152 | 0 | 0 |
| LS Electric | 697 | 134 | 23 |
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
| IDEC | 183 | 1 | 0 |
| Hanyoung Nux | 214 | 17 | 0 |
| Samwha | 45 | 9 | 0 |
| TDK / EPCOS | 29 | 0 | 0 |
| Shizuki | 42 | 0 | 0 |
| Nuintek | 135 | 20 | 0 |
| Mikro | 214 | 8 | 6 |
| SK | 3 | 0 | 0 |
| Ducati Energia | 2 | 0 | 0 |
| Selec | 28 | 0 | 0 |
| Delixi | 172 | 0 | 0 |
| Morele | 14 | 2 | 0 |
| EMIC | 86 | 13 | 5 |

## Phần còn thiếu

711/837 CAD chưa có lựa chọn giá phù hợp. Trong đó: 260 CAD đã xác định hãng nhưng thiếu mã/cấu hình hoặc nguồn giá đúng mã; 251 CAD chỉ xác định thư viện nguồn; 75 chưa rõ hãng; 14 nhãn hãng ứng viên; 111 phụ kiện phổ thông không áp hãng. Các mã ứng viên dựa kích thước của tụ Nuintek/Samwha chưa được đưa thành mã xác nhận. Không tự thay NX201A/MK201A bằng N201/R201.

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

Kiểm tra hồi quy: 53 tests về parser giá, liên kết CAD, bóc tách/báo giá và nhận diện hãng.

Cập nhật tiếp: thêm 73 dòng ABB 2026 (contactor 1SFL và rơ le nhiệt trang 117), gắn họ S200/SH200 theo trang 141–143; giữ dải chỉnh định rơ le thay vì gán thành dòng cố định. Xác nhận 4 cực cho MC-9a/4, MC-12a/4, MC-18a/4 theo [tài liệu LS, trang 14](https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf). Không đổi các MC-40 cũ thành MC-40a hoặc lấy điện áp cuộn hút theo suy đoán.

## Rà lại 293 CAD đã rõ hãng, ngày 14/10/2026

Đây là phân loại sau sửa, không còn gộp toàn bộ thành thiếu báo giá. Đợt trước có thêm 13 CAD dùng được giá đã có sẵn; đợt này thêm 18 CAD; không bổ sung hay thay đổi giá bán trong đợt này. Tổng có lựa chọn giá 126/837; còn 260 CAD đã xác định hãng chưa có lựa chọn phù hợp.

| Lý do hiện tại | CAD | Ý nghĩa |
| --- | ---: | --- |
| Chưa có mã/họ thiết bị đủ căn cứ | 56 | Hãng đã xác định, nhưng mã chỉ là ứng viên theo kích thước hoặc chưa đọc được. |
| Không thấy mã trong dữ liệu giá đã công bố | 137 | Không kết luận thị trường không có giá; cần thêm nguồn đúng mã, mã cũ hoặc mã đầy đủ. |
| Có chuỗi mã liên quan nhưng chưa khớp | 30 | Có thể khác thế hệ, khác loại, thiếu số cực/thông số hoặc chỉ là giá phụ kiện cho thiết bị. Không lấy giá theo chuỗi con. |
| Chưa có giá dưới nhãn hãng hiện tại | 37 | Có hãng ngoài 32 hãng bảng giá và hai nhãn Schneider RM6 kèm ghi chú; giá cùng hãng của thiết bị khác không thay thế được. |

Đã sửa: BV-D nhập từ sheet “MCB China” được phân loại đúng RCCB; S-T10/12/20/21/25/35/50 có 3 cực theo tài liệu hãng; XJ3-G là rơ le bảo vệ pha; Omron-S8FS-C05024J được bỏ dấu nối giữa tên hãng và mã; họ NP2-EA và iC60N thành lựa chọn có kiểm soát. Đối chiếu 1P+N yêu cầu đúng ký hiệu trung tính, không coi tương đương 1P. Giữ nguyên giá bán và ID nguồn.

Ví dụ phải giữ chưa khớp: ABB A2 trong CAD là 1P nhưng các dòng A2 đang có là 2P/3P/4P; ZCT120 khác ZCT120S; MC-40 khác MC-40a; bảng giá phụ kiện “SHT for ABN100c” không phải giá MCCB ABN100; MCCB Mitsubishi NF125-CV 4P không được lấy giá 2P/3P.

Chi tiết từng CAD: [library-verified-price-gaps.json](library-verified-price-gaps.json). Tái lập bằng `venv/Scripts/python.exe scripts/audit_library_price_gaps.py`. “related_code_only” chỉ là gợi ý tra cứu, không phải xác nhận giá đúng hoặc phê duyệt CAD.

Nguồn kiểm tra phân loại: [BV-D](https://www.mitsubishielectric.com/fa/sg_en/products/faspec/detail.page?category=ex&formNm=RCCB_RCBO_BV-D_4885&id=spec&kisyu=%2Flvcb&lang=2), [S-T](https://www.mitsubishielectric.com/dl/fa/document/catalog/lvsw/sh020011eng/SH%28NA%29020011ENG-A.pdf), [XJ3-G](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/xj3.html), [S8FS-C](https://www.ia.omron.com/products/family/3460/lineup.html), [NP2](https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/push-button/np2/catalog/NP2-Push-button-Catalog.pdf), [iC60N](https://eshop.se.com/sg/ic60n-miniature-circuit-breaker-3p-2a-c-curve-a9f74302.html).

## Kiểm tra đủ 837 thiết bị, ngày 14/10/2026

Đã kiểm tra toàn bộ 837 hồ sơ và 1.448 mặt bản vẽ: ID thiết bị/mặt chính, đường dẫn xem trước, tồn tại file nguồn DXF, cấu trúc SVG và liên kết giá. Không phát hiện file thiếu, mặt chính không hợp lệ, ID trùng hoặc SVG lỗi cấu trúc. Đây là kiểm tra dữ liệu/file; không phải duyệt hình học hoặc thông số điện bằng mắt cho mọi bản vẽ.

126 thiết bị có lựa chọn giá; 711 chưa đủ đối chiếu. Mỗi thiết bị giờ có lý do trạng thái giá trong API device-catalog: phụ kiện phổ thông, hãng ứng viên/chưa rõ, hãng từ thư viện nguồn, chưa xác nhận mã, chưa có dữ liệu giá của hãng, hoặc chưa khớp cấu hình. Giao diện hiển thị lý do đó khi chưa có lựa chọn giá, không chỉ yêu cầu bổ sung bảng giá chung chung.

[Báo cáo từng thiết bị](library-complete-audit.json), tái lập bằng `venv/Scripts/python.exe scripts/audit_complete_equipment_library.py`. 53 kiểm tra hồi quy đạt, gồm kiểm tra hộp thông báo và thao tác đánh dấu đã đọc không truy cập tài khoản khác.

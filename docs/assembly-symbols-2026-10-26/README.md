# Ký hiệu đại diện cho bộ thiết bị — đối chiếu tài liệu hãng

Ngày kiểm tra: 26/10/2026. Tài liệu tham khảo chức năng, không phải cấu hình mặc định hay BOM mua hàng.

## Kết luận về DOL / DOR và Start–Stop–HOA

Cấu hình có Start, Stop và công tắc Hand–Off–Auto tồn tại: Schneider liệt kê Form AC cho tổ hợp này; cũng liệt kê riêng phương án chỉ Start–Stop (Form A) hoặc HOA (Form C). Pilot light là tùy chọn riêng, có thể báo trạng thái chạy/dừng thay vì cảnh báo lỗi. Vì vậy lời khẳng định trước đó rằng mọi DOL/DOR đều có đủ Start–Stop–HOA cần được điều chỉnh.

File JOSEON đã đọc ghi DOL, không phải DOR. Không coi DOR là viết tắt chuẩn đồng nghĩa DOL; nếu khách hàng dùng DOR cho cấu hình riêng thì giữ quy ước trong yêu cầu dự án. Không đổi chữ trên bản vẽ.

Quy ước khách hàng đã xác nhận có thể dùng để đề xuất cấu hình: 1 Start + 1 Stop + 1 selector 3 vị trí; đèn chỉ khi có yêu cầu/nguồn xác nhận. Ghi rõ cơ sở yêu cầu, không mô tả là linh kiện đã nhìn thấy trên sơ đồ. Chức năng ba vị trí phải xác nhận; HOA và Forward-Off-Reverse không giống nhau.

## Sáu nhóm đã bổ sung

| Nhóm nhãn | Cấu tạo/chức năng để rà soát | Điều không được mặc định |
|---|---|---|
| DOL | Contactor và bảo vệ quá tải; biến thể Start/Stop, HOA, kết hợp, đèn | Không bắt buộc mọi bộ có đủ nút, selector, đèn; không lấy dòng MCB làm dòng motor |
| Reversing / FWD–REV | Bộ contactor thuận/nghịch, liên động, bảo vệ quá tải theo cấu hình | FWD/REV của biến tần hoặc một selector không chứng minh hai contactor |
| Star–delta / Y–Δ | Ba contactor line/star/delta ở cấu hình truyền thống, liên động, bảo vệ; điều khiển chuyển mạch theo sơ đồ | Không tự thêm timer rời nếu logic đã tích hợp; dải overload phụ thuộc vị trí lắp |
| ATS / ATSE | Chuyển nguồn, điều khiển và liên động; có loại tích hợp controller | Không luôn cộng hai MCCB và controller rời; ATS22 có thể là mã khởi động mềm |
| APFC / tủ bù tự động | Controller, các cấp tụ, đóng cắt và bảo vệ; cuộn kháng/CT theo cấu hình | Không coi controller là cả tủ; không mặc định CT kèm bộ hay mọi tủ đều có cuộn kháng |
| Soft starter / khởi động mềm | Khối bán dẫn, phối hợp bảo vệ; bypass/quá tải tích hợp hoặc rời theo model | Không cộng bypass ngoài khi bộ đã tích hợp; không đồng nhất mọi dòng sản phẩm |

## Cách áp dụng trong phần mềm

- Danh sách được nạp từ `app/data/assembly_symbol_knowledge.json`, qua `assembly_knowledge.py`, vào hợp đồng phân tích runtime cho ảnh/PDF/CAD.
- Mỗi thành phần chức năng suy ra được giữ là diễn giải (`basis=assembly_function`) cho đến khi có sơ đồ cấu hình, chú giải, tài liệu bộ hoặc yêu cầu dự án xác nhận.
- Thành phần đọc trực tiếp/yêu cầu rõ mới đi vào dòng thiết bị hoặc phụ kiện có evidence/request_quote.
- Phân biệt mua nguyên bộ với mua linh kiện. Thiết bị bảo vệ đã vẽ riêng upstream không cộng lại vào bộ.
- Không tự sinh SKU, dòng định mức, điện áp điều khiển, số cấp hoặc màu/số đèn từ tên viết tắt.

## Nguồn gốc tài liệu

- **dol — Schneider Electric**: [Contactor/overload DOL arrangements; stop control varies by assembly.](https://www.se.com/ie/en/faqs/FA139744/)
- **operators — Schneider Electric**: [Form AC combines Start-Stop and HOA; separate Start-Stop, HOA and pilot-light options exist.](https://productinfo.se.com/8502ct9701fvcs/8502ct9701-fv-contactors-and-starters/8502CT9701%20(bookmap)_0000088590.xml/$/ApplicationData-30CA9D56)
- **eaton — Eaton**: [Different configured starters carry Start/Stop or HOA with indicating lights.](https://www.eaton.com/ca/en-gb/products/low-voltage-power-distribution-control-systems/motor-control-centers/aftermarket-mcc-quick-ship-program.html)
- **reversing — Schneider Electric**: [Reversing contactors have two contactors with mechanical/electrical interlocking; starter versions include overload arrangements.](https://productinfo.se.com/8502ct9701fvcs/8502ct9701-fv-contactors-and-starters/8502CT9701%20(bookmap)_0000088590.xml/$/ReversingMagneticContactorsAndStart-01A631F0)
- **star_delta — Schneider Electric**: [Conventional star-delta uses line/star/delta contactors and interlocking; overload rating depends on circuit location.](https://productinfo.se.com/tesysgigainstallationguide/tesys-giga-series-giga-contactors-and-giga-thermal-overload-relays-installation-guide/English/TeSys%E2%84%A2%20Giga%20Series%20Giga%20Contactors%20and%20Giga%20Thermal%20Overload%20Relays%20Installation%20Guide_0000447511.xml/$/PanGu_3ContactorStar-Delta_0000449442)
- **ats — Socomec**: [ATyS g M is an I-0-II transfer product with integrated ATS controller.](https://apac.socomec.com/en/reference/93544010)
- **pfc — Schneider Electric**: [Capacitor bank contains controller, capacitor steps and dedicated switching; protection/reactors/CT supply vary by configuration.](https://productinfo.se.com/nadigest/5c51d645347bdf0001f1f280/Master/17704_MAIN%20(bookmap)_0000041932.xml/$/LowVoltageStandardAutomaticCapacitorBanksCPT_0000085054)
- **softstarter — Schneider Electric**: [ATS22 softstarter includes its end-of-start bypass contactor.](https://www.se.com/uk/en/faqs/FA272580/)
- **abb_softstarter — ABB**: [PSR built-in bypass, combined with MMS for motor overload/short-circuit protection.](https://electrification.us.abb.com/products/softstarters/psr-open-softstarters)

Đây là danh sách tham khảo có chọn lọc, không phải từ điển toàn bộ ký hiệu điện. Nhãn mơ hồ cần chú giải/nguồn bổ sung. Không sửa lại BOM JOSEON hoặc nhà nội trú trong thay đổi thư viện này.

# Rà soát hãng trong thư viện CAD

Tổng: 837 bản ghi.

Hãng trong hồ sơ hoặc bằng chứng CAD đã kiểm tra: 383. Hãng theo thư viện CAD nguồn: 251. Phụ kiện phổ thông: 111. Thiết bị còn thiếu bằng chứng hãng: 77. Hãng ứng viên: 15.

Rà soát bổ sung ngày 14/10/2026: đọc block lồng nhau trong DWG gốc (qua DXF), đối chiếu cả bản sao nguồn và kiểm tra các mặt chiếu. Khôi phục thêm 17 hãng: Schneider (PM2220, RMU E01/E02/E03), CHINT (hai cụm NP2 và Selector), DELAB, CML (5), KDE (2), Mikro MX100 và Deep Sea Electronics DSE8610. Bằng chứng, tên block, chữ nguồn, đường dẫn hãng và dấu SHA256 CAD được lưu trong app/data/library_manufacturer_evidence.json.

Lần rà soát trước chỉ đọc CAD tách đã bỏ sót chữ ở block con và mặt bên. Asian không phải hãng. Nhận diện hãng không xác nhận mã đặt hàng, thông số điện hoặc giá; những trường này vẫn phải đối chiếu riêng. Không gán hãng cho hình chỉ có ký hiệu điện hoặc bao hình mà không có bằng chứng nguồn.

Rà tiếp: xác định hãng Hanyoung Nux cho 4 hồ sơ có nhãn HYT (203, 204, 30, 304). 13 mẫu CD chỉ khớp hình và kích thước gần dòng HYT được lưu là hãng ứng viên, không xác nhận và không tự liên kết giá. Mẫu CD 4P 500A không được gán: CAD rộng 208 mm khác catalog 271 mm. Các mẫu TB cũng không được gán chỉ vì cùng số cực. Nguồn: [catalog HYT do hãng phát hành](https://www.components247.com/wp-content/uploads/2026/01/HYT_catalogue_en_251112.pdf).

Rà bộ điều khiển/rơ le: thêm 3 hãng Mikro từ bố trí mặt đặc trưng đối chiếu ảnh hãng: PFR, MX200A, NX201A/MK201A. Sửa mẫu ba núm ngang từ bảo vệ pha thành rơ le chạm đất; đây là nhận diện chức năng/họ, không xác nhận hậu tố nguồn và ngưỡng. Rơ le màn hình số được ghi Mikro ứng viên, còn cần phân biệt DIN330/MU250. Các ATS chưa có nhãn model vẫn chưa đủ cơ sở gán hãng.

## Các thiết bị còn thiếu nhãn hãng

| Thiết bị | Nhóm |
| --- | --- |
| Biến dòng đo lường BD1200A | BienDong |
| Biến dòng vuông 600 A | BienDong |
| Biến dòng đo lường 100/5 A | BienDong |
| Biến dòng đo lường 1000/5 A | BienDong |
| Biến dòng đo lường 1200/5 A | BienDong |
| Biến dòng đo lường 500/5 A | BienDong |
| Biến dòng đo lường MSQ-100 | BienDong |
| Biến dòng đo lường MSQ-30 | BienDong |
| Biến dòng đo lường MSQ-40 | BienDong |
| Biến dòng đo lường MSQ-60 | BienDong |
| Biến dòng bảo vệ P300/5 A | BienDong |
| Biến dòng đo lường RCT110 | BienDong |
| Biến dòng đo lường RCT35 | BienDong |
| Biến dòng đo lường RCT60 | BienDong |
| Biến dòng đo lường RCT90 | BienDong |
| Bộ điều khiển ATS · màn hình và phím | Bộ điều khiển |
| Bộ điều khiển ATS | Bộ điều khiển |
| Bộ điều khiển ATS · sơ đồ hai nguồn | Bộ điều khiển |
| Bộ giám sát pha | Bộ điều khiển |
| Rơ le giám sát pha | Bộ điều khiển |
| Rơ le giám sát pha · dạng ray hẹp | Bộ điều khiển |
| Biến tần · bảng phím tích hợp | Bộ điều khiển |
| Biến tần | Bộ điều khiển |
| Biến tần · kiểu BT 7.5 | Bộ điều khiển |
| Bộ ổn áp | Bộ điều khiển |
| Bộ ổn áp | Bộ điều khiển |
| Chống sét · mẫu CAD 123de9 | Chống sét |
| Chống sét · mẫu CAD 39fd8f | Chống sét |
| Chống sét · mẫu CAD f1b81c | Chống sét |
| Cuộn kháng ba pha lõi thép | Cuộn kháng |
| Dãy cầu đấu CD · 10 cực 30 A | Cầu đấu |
| Dãy cầu đấu CD · 1 cực 100 A | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 200 A | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 60 A | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 500 A | Cầu đấu |
| Chặn cuối dãy cầu đấu | Cầu đấu |
| Cầu đấu đơn CTS25 | Cầu đấu |
| Cầu đấu đơn CTS4 | Cầu đấu |
| Cầu đấu đơn CTS6 | Cầu đấu |
| Dãy cầu đấu TB · 12 cực 15 A | Cầu đấu |
| Dãy cầu đấu TB · 12 cực 20 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 150 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 15 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 200 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 20 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 300 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 30 A | Cầu đấu |
| Dãy cầu đấu TB · 4 cực 60 A | Cầu đấu |
| Dãy cầu đấu TB · 6 cực 20 A | Cầu đấu |
| Cầu đấu đơn UK3N | Cầu đấu |
| Đế cầu chì 1 cực | DenBaoNutNhanCauChiContactor |
| Dãy 3 đế cầu chì 1 cực · kiểu gạt | DenBaoNutNhanCauChiContactor |
| Dãy 3 đế cầu chì 1 cực · kiểu hộp | DenBaoNutNhanCauChiContactor |
| Dãy 5 đế cầu chì 1 cực · kiểu gạt | DenBaoNutNhanCauChiContactor |
| Đèn báo pha đầu tròn | DenBaoNutNhanCauChiContactor |
| Đèn báo pha đầu tròn | DenBaoNutNhanCauChiContactor |
| Đèn báo pha đầu phẳng | DenBaoNutNhanCauChiContactor |
| Đèn báo tín hiệu | DenBaoNutNhanCauChiContactor |
| Nút nhấn điều khiển mặt tủ | DenBaoNutNhanCauChiContactor |
| Công tắc xoay chọn chế độ | DenBaoNutNhanCauChiContactor |
| Biến áp · nhãn TR | Nguồn và biến áp |
| Nguồn · nhãn 24VAC | Nguồn và biến áp |
| Nguồn · nhãn 24VDC | Nguồn và biến áp |
| CẦU CHÌ · mẫu dự án | ProjectSamples |
| 125SRQ · mẫu dự án | ProjectSamples |
| RMU CCV-40.5kV | RMU |
| RMU CCVVV-40.5kV | RMU |
| Ampe kế kim gắn tủ | ThietBiDoLuongHienThi |
| Công tắc chọn dòng điện | ThietBiDoLuongHienThi |
| Công tơ điện cơ | ThietBiDoLuongHienThi |
| Công tơ điện cơ | ThietBiDoLuongHienThi |
| Đồng hồ đo điện dạng kim | ThietBiDoLuongHienThi |
| Đồng hồ đo điện kỹ thuật số | ThietBiDoLuongHienThi |
| Đồng hồ đo điện kỹ thuật số | ThietBiDoLuongHienThi |
| Vôn kế kim gắn tủ | ThietBiDoLuongHienThi |
| Ổ cắm công nghiệp 3 tiếp điểm | Ổ cắm |
| Ổ cắm công nghiệp 4 tiếp điểm | Ổ cắm |

## Các thiết bị có hãng ứng viên

| Thiết bị | Nhóm |
| --- | --- |
| Biến tần Mitsubishi FR-S500 (Mitsubishi Electric) | Biến tần |
| Rơ le số · cần đối chiếu chức năng (MIKRO) | Bộ điều khiển |
| Dãy cầu đấu CD · 10 cực 10 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 20 cực 20 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 100 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 150 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 300 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 400 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 3 cực 500 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 100 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 150 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 200 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 300 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 400 A (Hanyoung Nux) | Cầu đấu |
| Dãy cầu đấu CD · 4 cực 60 A (Hanyoung Nux) | Cầu đấu |

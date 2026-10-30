# Kiểm tra CHINT — 26/10/2026

Đã kiểm tra toàn bộ 43 nhóm CHINT đang hiển thị, gồm 159 mặt CAD.

- 159/159 mặt có tệp nguồn hợp lệ, đơn vị mm theo bản chuẩn hóa và không có lỗi DXF. Sửa đường tải của mặt thuộc hồ sơ thành viên khi gọi qua ID nhóm NXB-63; không cho lấy mặt không được liệt kê hoặc khác hãng.
- Bật màu và nét rõ cho CHINT như LS. Màu có sẵn được giữ; chỉ bổ sung RGB cho nét trung tính trong bản xuất. Đối chiếu 159 mặt xác nhận toàn bộ dữ liệu ngoài RGB giữ nguyên, gồm hình học, layer, độ dày nét và đối tượng điều khiển; tệp nguồn không bị sửa.
- 21 nhóm đủ 6 mặt, 22 nhóm còn thiếu, gồm 14 nhóm chỉ 1 mặt. Các nhóm chưa đủ không được đóng gói thành bộ đổi mặt đầy đủ. Không dựng thêm mặt hoặc ghép từ thiết bị khác.
- 21 bộ đủ mặt được xuất thành một block CHINT có tham số visibility CAD_FACE, đủ FRONT/REAR/SIDE-L/SIDE/TOP/BOTTOM, chỉ một mặt hiển thị ban đầu. AutoCAD Core kiểm tra cả 21 bộ: AUDIT 0 lỗi / 0 sửa. Đây là kiểm tra cấu trúc và trạng thái mặc định; chưa kiểm tra thao tác nút grip trong phiên AutoCAD giao diện của người dùng.
- Catalog NXM PDF trang 9–10 xác nhận mã số cực. Bổ sung Số cực cho đúng 11 dòng giá đã có liên kết CAD NXM-160S/250S; giữ nguyên ID, giá, dữ liệu gốc và lưu trước/sau. Không áp dụng suy diễn này cho những dòng chưa rà soát.
- API chi tiết dòng giá hiện ghép đúng 111/1.505 dòng, đều có ít nhất một bộ đủ 6 mặt. Còn 1.394 dòng chưa có liên kết CAD được xác minh theo cùng điều kiện của API. Con số cũ 288 gồm các liên kết tham khảo rộng hơn; không coi đó là số cấu hình đã xác minh.
- Các kiểm tra riêng NXC, NXR và NM8N đạt; 88 kiểm tra hồi quy đạt. Điều chỉnh kiểm tra giữ dữ liệu cũ theo phạm vi CHINT, không yêu cầu khôi phục 23 nhóm LS đã được chủ động ẩn trong đợt rà soát trước.
- Kiểm tra giao diện desktop/mobile dùng bản build có sẵn và dữ liệu CAD thật: chọn đúng 6 mặt của NXC-40, không yêu cầu colored=false. Đây là fixture, không phải phiên production đã đăng nhập.
- Hai API worker đã nạp bản sửa từng worker một; /health trả 200. Không khởi động lại Celery hoặc thay tiến trình xử lý tác vụ.

CHINT chưa đủ toàn bộ catalog: còn 22 nhóm thiếu mặt và 1.394 dòng giá chưa ghép CAD xác minh. Không đánh dấu hoàn tất và không gán CAD sai để giảm số thiếu.

## Bằng chứng

- [Kiểm tra nguồn và liên kết trước sửa](audit-before.json) · [sau sửa](audit-after.json)
- [Nét màu và 21 bộ đổi mặt](colour-export-validation.json)
- [11 dòng sửa số cực, dữ liệu trước/sau](nxm-pole-metadata-repair.json)
- [Danh sách còn cần bổ sung](supplement-queue.json) · [CSV toàn bộ dòng giá](price-cad-coverage.csv)
- [Kiểm tra UI](ui-check.json) · [desktop](chint-desktop.png) · [mobile](chint-mobile.png)
- [Ảnh CAD NXC-40](previews/TB-2b13370c59b7f4c5.png) · [NXB-63](previews/TB-e1b1231f6ae8fd19.png)

Nguồn đối chiếu số cực: catalog chính hãng [NXM-MCCB-Catalog.pdf](https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/catalog/NXM-MCCB-Catalog.pdf), SHA256 9130e6347eeb0c7bdf665afb22b9d3f6ff23ccf58605ca63763b63e58b42224f. Tệp gốc và ảnh trang mã được giữ trong workspace.

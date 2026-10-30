# Rà sâu MCCB, contactor và relay — 26/10/2026

## Kết quả cụ thể

- Bản DWG LS Russia `Dimensions_Metasol+(MC-6a-150a).dwg` đã tải nhưng chưa chuyển đổi trước đây. Sau chuyển đổi, nội dung tách rõ cột CONTACTOR DC và CONTACTOR 2a2b DC. Nhập đúng hai mặt trước/bên của cột DC thường cho MC-50a/65a và MC-75a/85a/100a, không dùng cột 2a2b hoặc tự tháo phụ kiện STEP. Không coi hình lỗ gá là mặt sau hoàn chỉnh.
- Tệp chính hãng 45195 ghi rõ ABS1003b/1004b/1203b/1204b và các hình 3P/4P riêng. Nhập hai hồ sơ ABS1003b và ABS1004b, mỗi hồ sơ trước/bên với thanh đầu nối gốc. Đơn vị gốc chưa khai báo nhưng kích thước native 400 đo đúng 400, toàn bộ hệ số kích thước bằng 1. Không thay đổi tỷ lệ hình học.
- Tổng bổ sung **4 hồ sơ / 8 mặt**, phục vụ **7 dòng giá** (5 contactor và 2 MCCB). Đây là CAD hai mặt, chưa phải bộ đủ sáu mặt.
- Đã chuyển đổi và xem nguồn chính hãng MR-8 số 50373: hai panel AC/DC riêng, ba hình chiếu. Không có đủ sáu hướng để khép gap. GMP22/GMP40 cũng có CAD nguồn; các dòng đang thiếu mặt, không phải không tìm thấy thiết bị.

## Sửa lỗi liên kết phát hiện trong lần rà sâu

`catalog_series_reference` từng bị nâng thành `source_family` trong bảng thông tin, làm một số khung MCCB khác nhau cùng tiền tố được coi là có CAD phù hợp. Đã giữ loại này ở mức tham khảo. Các mã hyphen đầy đủ như AN-06D3 và MR-4 vẫn được ghép theo đúng model sau khi lọc hãng/số cực/cuộn/tiếp điểm.

Năm dòng ABS202c, ABS103c FMU, ABS203c FMU, ABS104c FMU và ABS204c FMU mất liên kết không đủ căn cứ. Các liên kết sai khung khác cũng được bỏ khỏi menu của từng dòng giá; xem `coverage-changes.json`. Không dùng việc tìm thêm CAD để che mất các lỗi ghép cũ.

## Độ phủ sau sửa

517 dòng LS: **372 có liên kết CAD phù hợp, 347 có bộ đủ sáu mặt, 25 có CAD thiếu mặt, 145 chưa có liên kết được chứng minh**. Vẫn **170 gap**. Thư viện hiện **241 hồ sơ / 1.122 mặt**. Contactor có CAD phù hợp **66/69 dòng**; còn MC-6a DC, MC-150a DC và MW-9bB~22bB chưa có cấu hình được duyệt. MCCB có **109/127** dòng được liên kết; category này có cả phụ kiện như tay xoay, mô tơ và spreader, không thể gọi tất cả là thân máy cắt thiếu CAD.

60 kiểm tra hồi quy đạt. Đã cập nhật chỉ mục phục vụ CAD và triển khai lại worker API. Kiểm tra HTTP chi tiết và hash được lưu tại `../ls-all-cad-2026-10-24/live-api-targeted-final-20261026.json`. Chưa xác nhận sáu mặt hoặc chuyển mọi trạng thái bằng AutoCAD cho các bộ hai mặt mới.

## Bằng chứng

- [Contactor DC và liên kết giá](dc-additions.json)
- [ABS1003b/1004b và nhãn nguồn](mccb-additions.json)
- [Ảnh các mặt nhập](dc-contact-sheet.png)
- [Audit DXF và hash](dc-validation.json)
- [Toàn bộ thay đổi liên kết](coverage-changes.json)
- [Độ phủ tính lại](pricebook-cad-coverage.json)
- [Tổng hợp rà soát](review-result.json)

# Đối chiếu CAD LS với toàn bộ bảng giá

Đã kiểm tra 517 dòng giá LS: 328 dòng có ít nhất một bộ CAD họ đủ 6 mặt; 43 dòng có CAD nhưng thiếu mặt; 146 dòng chưa có CAD họ được xác minh.

Thư viện hiển thị 254 hồ sơ và 949 mặt CAD LS. Không có nhãn chưa xác định hoặc tệp DXF bị thiếu trong lần kiểm tra này.

## Quy tắc bắt buộc cho LS

- Phải có trước, sau, trái, phải, trên, dưới của cùng một biến thể; không ghép các mặt của biến thể khác nhau.
- Kiểm tra tệp CAD, đơn vị mm và audit trước khi dùng cho bố trí; kích thước nhập tay không thay thế CAD còn thiếu.
- Thiếu CAD hoặc thiếu mặt thì yêu cầu bổ sung và chặn bố trí; không dùng hộp kích thước hoặc CAD hãng khác thay thế LS.
- CAD họ có thể dùng cho nhiều mã, nhưng vẫn phải khớp số cực, AC/DC, tiếp điểm phụ, kiểu lắp và đầu nối.
- Các giá trị Icu/Icn/Inc trong tên chỉ tham chiếu bảng giá. CAD không xác nhận dòng cắt ở điện áp làm việc hoặc SKU đặt hàng.

## Độ phủ theo loại

| Loại | Dòng giá | Đủ 6 mặt CAD họ | Có CAD còn thiếu mặt | Chưa có CAD |
|---|---:|---:|---:|---:|
| ACB | 100 | 100 | 0 | 0 |
| ACCESSORY | 88 | 6 | 0 | 82 |
| AUX_CONTACT | 4 | 4 | 0 | 0 |
| CONTACTOR | 69 | 59 | 5 | 5 |
| ELCB | 17 | 10 | 1 | 6 |
| MCB | 32 | 0 | 0 | 32 |
| MCCB | 127 | 105 | 20 | 2 |
| METER | 3 | 1 | 0 | 2 |
| MOTOR_PROTECTION | 18 | 18 | 0 | 0 |
| RCBO | 8 | 6 | 0 | 2 |
| RCCB | 10 | 10 | 0 | 0 |
| RELAY | 17 | 9 | 8 | 0 |
| SPD | 15 | 0 | 0 | 15 |
| THERMAL_RELAY | 9 | 0 | 9 | 0 |

## Phần còn thiếu

Danh sách yêu cầu bổ sung ghi riêng từng mã giá và từng mặt còn thiếu trong [cad-supplement-queue.json](cad-supplement-queue.json). Không đánh dấu hoàn tất toàn bộ LS khi danh sách này còn dòng. Các nguồn không tương thích đời sản phẩm, BK AC/SPD hoặc cấu hình cuộn hút được giữ ngoài thư viện đã xác minh; xem [source-gap-review.json](source-gap-review.json).

## Giao diện và kiểm tra

FE đã đẩy commit 929c28fb; Vercel báo triển khai thành công. Hiển thị trạng thái 6 mặt theo biến thể, đặt tên tệp CAD LS theo họ thiết bị và mặt nhìn; đã bỏ Xem tài liệu và các mục trống.
32 bài kiểm tra về đủ mặt LS, cấu hình AC/DC/tiếp điểm phụ, bao hình, sản phẩm và quyền truy cập đã đạt. Kết quả kiểm tra từng tệp bổ sung ghi trong [six-view-validation.json](six-view-validation.json).

Chi tiết từng dòng giá: [CSV](pricebook-cad-coverage.csv), [JSON](pricebook-cad-coverage.json). Nguồn CAD và SHA256: [ls-full-faces-2026-10-20.json](../ls-full-faces-2026-10-20.json).

## Kết quả kiểm tra cuối đợt

- 640 mặt bổ sung: mm, audit DXF, checksum, bao hình, SVG và nét hình học đạt.
- 99 họ STEP: đủ 6 mặt, bao hình bố trí và một mặt bên làm nguồn chiều sâu đạt.
- 84 lượt đọc DXF/SVG theo mã góc nhìn công khai qua hàm phục vụ API đạt.
- FE commit 929c28fb: Vercel thành công; bundle đang chạy có trạng thái 6 mặt, tên tải CAD LS và không còn Xem tài liệu. API health trả 200.

[Danh sách 189 dòng LS cần bổ sung CAD/mặt còn thiếu (CSV)](ls-cad-can-bo-sung.csv). Chưa thể chốt đầy đủ 100% LS khi các dòng này chưa có nguồn CAD đúng họ/cấu hình và đủ mặt được xác minh.

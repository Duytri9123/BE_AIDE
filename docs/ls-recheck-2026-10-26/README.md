# Kiểm tra lại LS và bảng giá — 26/10/2026

Đã chạy lại audit trên dữ liệu hiện tại và kiểm tra HTTP API đang chạy. Danh sách 170 gap khớp hoàn toàn với bảng tồn đọng trước đó.

| Chỉ tiêu | Kết quả |
|---|---:|
| Dòng giá LS | 517 |
| Có CAD họ liên kết phù hợp | 372 |
| Có ít nhất một bộ sáu mặt cùng biến thể | 347 |
| Có CAD nhưng thiếu mặt | 25 |
| Chưa có CAD phù hợp | 145 |
| Tổng dòng chưa hoàn tất CAD | 170 |
| Hồ sơ / mặt CAD công khai | 237 / 1.114 |

## Tồn đọng CAD

| Nhóm | Chưa có CAD phù hợp | Có CAD còn thiếu mặt | Tổng |
|---|---:|---:|---:|
| Phụ kiện ACCESSORY | 68 | 0 | 68 |
| MCB | 32 | 0 | 32 |
| MCCB | 13 | 9 | 22 |
| SPD | 13 | 2 | 15 |
| Contactor | 8 | 6 | 14 |
| Relay | 0 | 8 | 8 |
| ELCB | 7 | 0 | 7 |
| RCBO | 2 | 0 | 2 |
| Đồng hồ METER | 2 | 0 | 2 |

Một số điểm còn vướng: LA chưa xác định cơ cấu gá MMS-32 hay MMS-63/100; contactor DC có nguồn khác tiếp điểm; các bộ BK05, MR, GMP và một số MCCB thiếu hướng nhìn. Những mặt không có nguồn không được tự dựng để giảm số gap. CAD họ đủ sáu mặt vẫn chưa xác nhận mã đặt hàng hoặc phê duyệt gia công.

## Bảng giá

- 517/517 dòng có giá dương hợp lệ, nguồn, trang tài liệu và SHA256; không có ID trùng.
- 517/517 dòng ghi chưa VAT, hiệu lực 01/10/2026. Tệp PDF nguồn trên máy chủ tồn tại, SHA256 khớp dữ liệu.
- Có 84 nhóm trùng tên SKU; nhiều nhóm khác dải dòng/cấu hình, nên không thể xóa theo SKU đơn thuần.
- Có 5 cặp GMP tương đương cấu hình và cùng giá giữa trang 4 và 8: GMP22-2P, GMP22-3P, GMP40-2P, GMP40-3P (1a1b), GMP60-T (1c). Đây là phần cần cân nhắc chuẩn hóa hiển thị; hiện giữ hai ID nguồn để truy vết. Không phát hiện xung đột giá trong nhóm tương đương này. Không thay giá hoặc xóa dòng trong lần kiểm tra.

## API đang chạy

Health trả 200; 13 kiểm tra chi tiết dòng giá đạt; hai ảnh SPD trả 200; 58/58 tệp nguồn tải qua HTTP khớp hash; ba mẫu tải visibility có mm và DXF audit không lỗi. LA vẫn không có liên kết CAD chưa được duyệt. Chưa kiểm tra riêng tên miền ngoài hoặc chuyển trạng thái AutoCAD cho toàn bộ bộ mới.

## Bằng chứng

- [Audit hiện tại](pricebook-cad-coverage.json) · [CSV](pricebook-cad-coverage.csv)
- [Kiểm tra toàn vẹn giá](price-integrity.json) · [Rà soát dòng lặp](repeated-row-review.json)
- [Kiểm tra HTTP lần này](live-api-recheck.json)
- [Lý do và bằng chứng cần bổ sung cho từng gap](../ls-all-cad-2026-10-24/remaining-gap-dispositions-20261026.csv)

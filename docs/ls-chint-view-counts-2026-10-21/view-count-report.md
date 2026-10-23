# Kiểm tra số mặt CAD LS/CHINT

Kết quả đếm trên danh sách hiển thị hiện tại, có kiểm tra tệp tồn tại. Đếm tệp riêng với đếm hướng nhìn: một mặt bên chung chưa xác định trái/phải không thay thế hai mặt; không ghép các biến thể khác nhau để tạo bộ đủ 6 mặt.

| Hãng | Mục hiển thị | Chỉ 1 mặt | Có 2–5 mặt | Có ≥6 tệp nhưng thiếu hướng | Có bộ đủ 6 hướng |
|---|---:|---:|---:|---:|---:|
| LS | 264 | 61 | 89 | 3 | 111 |
| CHINT | 37 | 18 | 14 | 0 | 5 |

Tổng cộng còn 79 mục chỉ có 1 mặt và 185 mục chưa có bộ đủ 6 hướng. Không có tham chiếu tệp bị thiếu trong các mục này. Đây là số mục thư viện, không phải số mã thiết bị trong bảng giá. Một họ CAD có thể tham chiếu nhiều mã; một mục hiển thị có thể gộp nhiều thư mục nguồn.

## Ba mục LS có nhiều tệp nhưng chưa đủ hướng

- LS · Contactor · MC-35 / MC-40 / MC-50 / MC-63 · 3P: 6 tệp; thiếu ở bộ tốt nhất: Mặt trước, Mặt bên trái, Mặt bên phải, Mặt trên, Mặt dưới.
- LS · Contactor · MC-9 / MC-12 / MC-18 / MC-25 / MC-32 · 3P: 7 tệp; thiếu ở bộ tốt nhất: Mặt trước, Mặt bên trái, Mặt bên phải, Mặt trên, Mặt dưới.
- LS · Contactor · MC-95 / MC-65 / MC-75 / MC-85 · 3P: 6 tệp; thiếu ở bộ tốt nhất: Mặt trước, Mặt bên trái, Mặt bên phải, Mặt trên, Mặt dưới.

## Danh sách chi tiết

- [79 mục chỉ có một mặt](one-view-items.csv)
- [185 mục còn thiếu hướng](incomplete-items.csv)
- [Toàn bộ 301 mục](all-items.csv)
- [Chi tiết biến thể, từng mặt và đường dẫn hồ sơ nguồn](all-items.json)
- [Đếm riêng theo thư mục nguồn, gồm các thư mục đã ẩn](source-folder-counts.json)

Các mặt đã xác định được hướng vẫn có thể thiếu các hướng khác; không đánh dấu đủ bộ chỉ vì hết nhãn chưa xác định. Báo cáo này không sửa hoặc xóa các CAD còn nhận diện được.

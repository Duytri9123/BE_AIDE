# Cập nhật giá CHINT 16/10/2026

Đã bổ sung 23 dòng giá bán công khai: 21 biến thể ATS NZ7-125 và 2 dòng bộ phận RT36-00. Sửa phân loại 26 NCH8 và 42 công tắc xoay NP2 từ bảng giá CHINT 2026.

| Thiết bị | Dòng giá hiển thị trong thư viện |
| --- | ---: |
| Timer CHINT KG316T | 1 |
| Contactor CHINT NCH8-20 / NCH8-25 · 2P | 6 |
| Selector CHINT NP2 | 42 |
| Fuse Assembly CHINT RT36-00 · 160A | 2 |
| ATS CHINT NZ7-125 | 7 |

RT36-00: ruột gG 160A 170.000 VND (BluePower Automation/Shopee, hàng đặt trước); đế 1P 69.100 VND (Bảo An Automation). Giá tham khảo từ trang công khai/index đã đọc ngày 16/10/2026; VAT và giá hiện hành cần xác nhận. Không cộng thành giá cả bộ và không xác nhận khả năng chèn CAD. Nguồn, trích đoạn và thời điểm đọc được lưu cùng bản ghi trong web_catalog_offers.json.

Đối chiếu API trực tiếp: bảng giá tổng có 2 dòng RT36-00; thư viện có đúng 2 dòng bộ phận, 6 lựa chọn NCH8, 42 NP2 xoay, 7 NZ7-125 4P. Timer KG316T giữ 601.700 VND.

Phạm vi đợt này là nhóm CHINT được đối chiếu. Các mã chưa xác nhận như relay RJ25-CL hoặc biến áp chưa rõ mã chưa được gán giá của thiết bị khác.


## Kiểm tra

- 49 kiểm thử backend đạt.
- Vite production build đạt.
- Playwright dùng dữ liệu xuất từ API thực: thư viện desktop/mobile và bảng giá chung đạt; kiểm tra RT36, NCH8, NP2, NZ7; không có lỗi trình duyệt.
- TypeScript toàn dự án còn lỗi tại các mô-đun CAD/agent và test runner ngoài phần sửa; build production vẫn thành công.
- Ảnh kiểm tra: outputs/chint-external-prices/rt36-desktop.png và rt36-mobile.png tại workspace cha.

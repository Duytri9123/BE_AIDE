# CHINT — kiểm tra ngày 2026-10-23

Đã bổ sung 7 họ contactor NXC (42 mặt, 15 dòng giá) và 4 cấu hình rơ-le nhiệt NXR (24 mặt, 23 dòng giá). Cả 11 mẫu có sáu hướng thực từ nguồn STEP hãng, đơn vị mm, đúng trục lắp đã xem trực tiếp. Không coi CAD là phê duyệt thông số điện hay mã đặt hàng.

Đã sửa 40 dòng giá bị đọc nhầm cột contactor tương thích NXC thành tên sản phẩm: trả lại đúng mã rơ-le NXR và dải chỉnh định Ir. Giữ nguyên ID, giá và thông tin lắp tương thích; lưu nguyên dữ liệu trước sửa. Cấu hình ba pha có căn cứ catalog NXR trang 1 và đối chiếu đầu nối CAD. Bộ chuẩn hóa chỉ áp dụng đúng hash và trang PDF bảng giá đã kiểm tra.

CHINT hiện ghép 288/1.505 dòng giá; còn 1.217 dòng cần nguồn/ghép chính xác. Có 43 hồ sơ hiển thị, 21 hồ sơ đủ sáu hướng; 22 hồ sơ cũ còn thiếu hướng, trong đó 14 hồ sơ chỉ một hình. Đây chưa phải thư viện CHINT hoàn chỉnh.

Kiểm tra dữ liệu giao diện: `nxc-verification.json`, `nxr-verification.json`; giữ đủ 953 hồ sơ trước đợt cập nhật, hiện 967 hồ sơ toàn thư viện. 26 kiểm thử liên quan đạt. API cục bộ `/health` trả 200; chưa kiểm tra giao diện bằng phiên người dùng đã đăng nhập.

Nguồn tải: 35 STEP trong `native-source-inventory.json`, DWG NXR nguyên bản và kho RAR từ CHINT Nga. Tải được không đồng nghĩa đủ điều kiện hiển thị. NXR-25: DWG hãng chỉ ba hình; RAR Nga không chứa mã này. Nguồn Hàn có niêm yết nhưng chứng chỉ TLS hết hạn; chint.net trả 403. Không dựng thêm mặt giả. NXR-200, NXR-630 200–630 A và NXC120/160/185/500–630 còn giữ ngoài đợt công bố vì lỗi hình học hoặc cấu hình chưa thống nhất; xem `nxr-import.json` và `nxc-import.json`.

Nguồn chính: https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/nxc.html và https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/nxr.html . Ghi nhãn mặt ngắn FRONT / REAR / SIDE-L / SIDE / TOP / BOTTOM.

## Tiếp tục NM8N-125

Bổ sung 3 cấu hình 1P/3P/4P, đủ 18 mặt, ghép 61 dòng giá. Bản 1P có khắc 125 A: chỉ ghép 125 A. Bản 3P và 4P dùng họ TM, 16–125 A, C/S/H; mã 4C giữ đúng trong lựa chọn, cấu trúc bảo vệ cực N cần theo mã đặt hàng. Bản 2P nguồn hãng có khắc 160 A, giữ ngoài công bố vì xung đột với tên nguồn NM8N-125.

Đã bổ sung điện áp công bố Icu/Ics cho 80 dòng giá NM8N-125 theo bảng catalog trang 4; giữ nguyên giá/ID. 1P C tại 220/230/240 V AC; C/S/H nhiều cực tại 380/400/415 V AC. Không suy sang DC. Chuẩn hóa áp dụng đúng bản PDF bảng giá và trang 39–42; từ chối thông số mâu thuẫn.

Bản 4P: xuất BRep chính xác có một mặt rỗng; dùng năm mặt BRep và một mặt chiếu cạnh hiển thị từ cùng mô hình STEP gốc. Cả sáu mặt đã xem trực tiếp, đối ứng cùng kích thước; không cắt/xóa hay dựng lại thân máy. Lưu dấu vết theo từng mặt trong nguồn đã rà soát.

Kiểm chứng công khai: `nm8n125-verification.json`; nguồn và dải mã: `nm8n125-import.json`; điện áp dòng cắt: `nm8n125-rating-corrections.json`.

Lượt hoàn tất NM8N đã chạy hết: đo lại và xác minh 3.288 tham chiếu hình chiếu, không loại thêm nguồn do thay đổi hoặc chú thích; kiểm tra NXC/NXR/NM8N đạt, chỉ mục nhận diện gồm 1.912 hồ sơ / 4.580 mặt khai báo. Các số toàn thư viện bao gồm hồ sơ nội bộ, không đồng nghĩa tất cả đã được công bố.

# Bổ sung phân loại CAD — 2026-10-20

Đã bổ sung mã loại từ vai trò ghi rõ trong hồ sơ hiện có cho 145 hồ sơ, tương ứng 236 asset đang được nạp. Asset chưa phân loại giảm từ 238 xuống 2.

Các nhóm được bổ sung gồm cầu đấu (36 hồ sơ), khóa tủ (26), giá đỡ cách điện (21), bản lề (15), rơ le nhiệt (6), đầu cos (6), quạt/lưới lọc/lưới bảo vệ, ổ cắm và phụ kiện cơ khí. Chỉ thêm loại chức năng; không xác nhận hãng, mã đặt hàng, dòng, khả năng cắt hay lựa chọn tự động.

Sửa 58 nhãn hiển thị vẫn ghi chưa xác định dù huong_nhin của hồ sơ đã có giá trị cụ thể. Bổ sung ánh xạ cho mặt bên trái/phải, hình trục đo, mặt đế gá theo bản vẽ: 22 hình có nhãn rõ được bộ nạp nhận diện. Đây là sửa cách đọc nhãn, không suy đoán hướng từ hình dạng.

Còn 2 asset chưa xác định loại: nguồn mang nhãn 24VAC và 24VDC. Nhãn điện áp chưa đủ để kết luận cấu tạo nguồn. Còn 492 asset chưa xác nhận hướng nhìn; không đổi sang mặt trước/bên/trên để làm giảm số lượng trên báo cáo.

Kiểm tra:
- 10 unittest về phân biệt mặt, ghép bao hình CAD, tìm kiếm: đạt.
- 244 file CAD liên quan giữ nguyên SHA256.
- Các trường hãng, mã sản phẩm, thông số, auto_select, needs_review và điều kiện chèn của từng hình giữ nguyên.
- SQLite/FTS và chỉ mục trình duyệt đã đồng bộ đúng các hồ sơ thay đổi.
- Tìm kiếm bản lề, cầu đấu, rơ le nhiệt trả về mã loại tương ứng.

Bằng chứng và thống kê: report.json. Bản sao hồ sơ trước thay đổi: before/.
Tái tạo: scripts/complete_explicit_catalog_roles.py. Script chỉ bổ sung vai trò thiếu, không tự gán hướng nhìn cho các hình chưa xác định.

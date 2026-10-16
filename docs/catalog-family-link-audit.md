# Rà soát ghép thông tin bảng giá với CAD — 16/10/2026

Đã rà toàn bộ 1471 hồ sơ nguồn (1313 đang dùng; giao diện gộp thành 1304 mục), đối chiếu 9581 dòng bảng giá/website hiện có.

Ghép theo hãng/dòng hoặc chức năng: 161 hồ sơ, 1535 dòng thông tin. Dòng liên quan cùng hãng/loại: 74 hồ sơ, 4307 dòng; ghi riêng vì mã/khung có thể khác. Không lấy giá. Có bảng tham khảo không chứng minh đã nhận diện đúng dòng thiết bị.

- Giữ mọi biến thể trong dòng đã ghép, kể cả cùng mã ở nhiều nguồn. Hãng, mã, thông số, tài liệu được giữ; giá để `---`.
- Đọc số cực từ nhận diện CAD; không lấy các mã đã bổ sung vào từ khóa tìm kiếm làm bằng chứng nhận diện.
- BKN-LS 1P/2P/3P: mỗi cấu hình có hai biến thể BKN sẵn có tương ứng; không lấy LA125H thay cho BKN.
- TIMER 24H CHINT: KG316T AC220V, 24h/7, NO, mã hàng 309010, bảng CHINT trang 73; không lấy JSS48A thay cho timer lịch.
- MC12AF: các biến thể MC-12a; S8FS-C05024J lấy đúng mã nguồn; mở rộng cùng cơ chế cho toàn bộ hồ sơ.
- Chặn ghép nhầm loại, ghép số thuần, và tiền tố LC1D9 với LC1D95; đọc các mã thành viên để hỗ trợ dải dòng.
- 69 hồ sơ đang dùng chưa có mã thương mại tham khảo cụ thể. Số này khác số hồ sơ chưa ghép đúng dòng: không dùng việc bảng có dữ liệu để kết luận tất cả đã đúng.

Chi tiết từng hồ sơ: `catalog-family-link-audit.json`.

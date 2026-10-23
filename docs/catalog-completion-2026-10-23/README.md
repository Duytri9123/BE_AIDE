# Cập nhật thư viện CAD — 23/10/2026

Đã bổ sung Mitsubishi: 19 cấu hình, 114 mặt và 102 dòng giá. Tổng nhóm nhập STEP đã kiểm tra là 230 cấu hình / 1.380 mặt / 2.583 dòng giá, tất cả mã giá dự kiến có trong dữ liệu hiển thị khách hàng.

Các nhóm mới gồm S-N, SD-N, S-T/SD-T đầu nối SQ và TH-N. Tách AC/DC, đầu nối lò xo, số cực và các mã được hãng phục vụ cùng nguồn CAD. S-N150 dùng hệ trục riêng được đối chiếu bản vẽ BH782D801-A. TH-N600 ghi rõ đầu vào qua biến dòng ngoài thứ cấp 5 A.

Kích thước được đo từ DXF chiếu nguyên mô hình, giữ các phần nhô và trạng thái gốc. Không dùng kích thước bao STEP sơ bộ (có thể chứa giới hạn lỏng của mặt spline) thay cho kích thước hình chiếu thực tế. Không suy Icu/Ics từ hình dáng hay áp một giá trị kA cho mọi điện áp.

Mitsubishi đã ghép 2.583/3.184 dòng giá; **còn 601 dòng**, không tuyên bố thư viện đã đầy đủ. Xem `mitsubishi-batch-result.json` và bảng đối chiếu toàn bộ tại `../all-brands-price-cad-links-2026-10-22/all-price-rows.csv`.

Đã tải riêng 19 kho CAD đo lường gốc, liên quan 22 dòng giá. Chúng chưa được tính vào số ghép mới. ME96SSEB có mặt trước, mặt bên và lỗ khoét cánh; EMU4-BM1-MB và EMU-CT5-A/50-A mới thấy hai mặt. Không đổi lỗ khoét thành mặt sau hoặc lật một hình để giả mặt còn thiếu. Chi tiết: `meter-native-pending.json`.

32 kiểm tra hồi quy đạt sau sửa bộ lọc và nhận diện từ nhãn CAD; 18 kiểm tra tập trung cho cache hash và nhận diện cũng đạt. Đối chiếu 3.104 tham chiếu kích thước hiện hành không phải gỡ bản đo nào ở bước cuối. Kiểm tra hash DXF/SVG, đơn vị mm, audit DXF, sáu vai trò mặt và mọi SKU dự kiến trong dữ liệu khách hàng đã đạt cho 230 cấu hình Mitsubishi.

API đã nạp mã hiện tại. Phát hiện bốn bộ uvicorn chạy trùng cổng 8000; sau khi hàng đợi tác vụ không còn việc đang chạy, giữ một bộ hai worker và dừng ba bản trùng. Health trực tiếp trả 200. API thư viện không có phiên đăng nhập trả 401 theo cơ chế bảo vệ, nên kiểm tra dữ liệu khách hàng dùng các hàm dịch vụ thật, không khẳng định đã duyệt bằng tài khoản người dùng trên website.

FE trước đó đã đẩy commit 3398c80f và Vercel triển khai thành công; đợt này tiếp tục cập nhật CAD và dữ liệu backend.

Bổ sung Shihlin BM250-SN 3P và 4P: 2 cấu hình / 12 mặt / 2 dòng giá riêng theo số cực. Kích thước CAD là 105 × 165 × 91,54 mm và 140 × 165 × 91,8 mm. Bản 4P gốc đặt nghiêng nhẹ trong hệ tọa độ; hướng chiếu được xác định từ các mặt phẳng thân vỏ, không kéo hình để khớp kích thước. Cả sáu mặt đã được xem trực tiếp sau chiếu. Bản giá BM250-SN 2P chưa có mô hình 2P tương ứng trong kho hãng, nên không ghép sang 3P/4P. Xem `shihlin-bm250-import.json`; kết quả kiểm tra dữ liệu khách hàng được ghi riêng trong `shihlin-bm250-verification.json`.

Chỉ mục AI đã được tạo lại ở chế độ chỉ cập nhật chỉ mục, không sửa nhận diện hồ sơ gốc: 1.889 hồ sơ, 4.442 tham chiếu mặt. Kiểm kê nội bộ còn 621 hướng nhìn chưa xác định và 2 hồ sơ thiếu trường phân loại; đây là danh sách cần xử lý, không phải các CAD đã được duyệt để hiển thị hoặc chèn. Bộ nạp giữ chính sách nhận diện, đơn vị và quyền chèn; không biến các mục đó thành thiết bị đã xác minh.

Đối chiếu danh mục trước/sau: giữ nguyên 942 hồ sơ đã hiển thị, thêm đúng 2 hồ sơ Shihlin mới, tổng 944; không mất hồ sơ cũ khi áp bộ lọc sớm. Nhận diện có bằng chứng từ nhãn CAD vẫn được chấp nhận khi hash và phiên bản hồ sơ khớp. File thay đổi thì phải xác minh lại. Danh sách thiếu hướng nhìn hiện tại: `visible-face-gaps.csv` và `visible-face-gaps.json`; số dòng giá đã ghép và số mặt đủ sáu hướng là hai chỉ tiêu khác nhau.

Rà hướng nhìn theo hồ sơ đang hiển thị: Mitsubishi còn 33 hồ sơ cũ thiếu hướng; LS 114, CHINT 22, ABB 92, Schneider Electric 149 và Shihlin 16. Số này đếm vai trò hướng nhìn ở cấp hồ sơ, không chứng nhận mọi mã đặt hàng dùng chung mọi mặt. Các 21 cấu hình bổ sung trong đợt này đều có sáu hướng riêng.


## Đợt tiếp theo: nguồn CAD Shihlin bổ sung

Đã tải 7 archive CAD gốc từ 17 trang sản phẩm hãng: BM30, BM100, BM125, BM160, BM250, BM630s và BM1000/1200/1600. Archive BM125 thực tế chứa các thành viên tên BM100; không tự đổi tên và ghép theo kích thước. Các nguồn có hash SHA-256 và danh sách thành viên tại `Shihlin/NguonBenNgoai/PRIMARY-EXPANSION-20261023/downloads.json`.

Các cấu hình đang xuất bản/kiểm chứng: BM30-CN 2P, 3P; BM1000-HS 3P; BM630s-STA/LTA/HTA/RTA 3P và LTA/HTA 4P. Mỗi cấu hình có sáu hình chiếu từ STEP gốc, không dựng mặt giả. BM30 và BM630s dùng trục lắp riêng đã đối chiếu tay gạt/đầu cực/N.

Bảng giá trang 7 tách BM630s có/không thanh đồng. CAD gốc giữ thanh nối, nên chỉ gắn các dòng có thanh đồng; không xóa thanh nối để ghép giá thấp hơn. Hồ sơ mới dùng phạm vi ID dòng nguồn tường minh để chặn ghép rộng theo tên mã.

BM1000-HS: thân CAD 210 × 406 mm và chi tiết sau 346 mm khớp bản kích thước hãng; kích thước bao cả đầu nối lớn hơn thân và được đo riêng, không ép tỷ lệ về 406 mm. Dòng cắt luôn kèm điện áp và tiêu chuẩn từ catalog, không suy từ hình học.

Trạng thái kiểm chứng cuối đợt: xem `shihlin-expansion-verification.json`; chưa được coi mọi hãng đã đầy đủ.


Kết quả cuối đợt bổ sung Shihlin: 9 cấu hình / 54 hình chiếu / 9 dòng giá mới, đã kiểm tra bằng dịch vụ dữ liệu khách hàng thật. Tổng Shihlin: 33/152 dòng giá đã liên kết, còn 119; 27 hồ sơ công khai, 11 hồ sơ đủ sáu hướng và 16 hồ sơ cũ còn thiếu hướng. Tổng thư viện công khai 953 hồ sơ; mọi hồ sơ trước đợt được giữ. Mitsubishi vẫn 230 cấu hình sáu mặt / 2.583 dòng giá đã kiểm chứng. 17 kiểm tra liên quan thay đổi đều đạt. Một kiểm tra cũ phụ thuộc tên hiển thị LS thất bại do kỳ vọng tên cũ; không sửa tên LS ngoài phạm vi đợt này.

Đã sửa một dòng nhập nhầm BM630s-LTA thành MT-400N (bộ đóng/mở điện MCCB) theo bảng giá gốc trang 7, giá 14.258.000 đồng. Giữ nguyên PDF nguồn và lưu đầy đủ dòng nhập trước/sau trong `shihlin-price-row-correction.json`. Hai worker API đã nạp thay đổi; tình trạng chi tiết trong `shihlin-expansion-runtime.json`. FE không thay đổi trong đợt này.

# Chi tiết tủ điện và bằng chứng cần lưu

## Cấu trúc hồ sơ chi tiết

Mỗi chi tiết cần một ID vật lý riêng và nhóm hình chiếu tham chiếu đến ID đó. Hồ sơ gồm loại, chức năng, model/biến thể, hãng có căn cứ, tệp/handle hoặc trang nguồn, SHA256, đơn vị, mặt sở hữu, bao hình, mốc gá, hướng lắp, vật liệu, quan hệ gá/nối điện, số lượng vật lý và trạng thái từng trường. `null` là chưa biết; `0` chỉ dùng khi đã đo hoặc được chỉ rõ bằng 0.

Tách `envelope`, `mounting_pattern`, `operator_envelope`, `panel_cutout` và `terminal_map`. Bao hình thiết bị không phải hình lỗ khoét. Một front view và một side view của cùng MCCB là hai bằng chứng cho một thân MCCB; phụ kiện tay xoay thực tế lại là một chi tiết riêng nếu được chọn.

## Bảng thiết kế và kiểm tra theo chi tiết

| Chi tiết | Dữ liệu bắt buộc bổ sung vào hồ sơ | Kiểm tra và tín hiệu học hữu ích |
| --- | --- | --- |
| Thân vỏ và khung | H W D thân, chiều dày, vật liệu, mép gấp, vùng hữu dụng, điểm liên kết | Phân biệt kích thước thân/tổng; học lựa chọn vỏ sau khi kiểm tra toàn bộ chi tiết |
| Cánh ngoài | Đường bao, mặt trong/ngoài, trục bản lề, gioăng, khóa, góc mở | Va chạm khi đóng/mở; học đổi vị trí thiết bị do cấn khóa hoặc gân |
| Cánh trong | Mốc sâu, bản lề, điểm tháo, vùng thao tác và che chắn | Tách thân CB khỏi mặt tay gạt; học vị trí thao tác khi đã duyệt |
| Hèm và gân tăng cứng | Tiết diện, độ nhô, mối nối và mặt sở hữu | Không coi đường biên FRONT là tiết diện đã biết; kiểm tra gá chịu lực |
| Tấm lắp và đố gá | Đường bao, chiều dày, mốc sâu, lỗ/ren, khoảng đỡ, tải cho phép | Có đường truyền lực tới khung; học cách chia đố với loại thiết bị cụ thể |
| Nóc và mái che | Độ dốc, phần nhô, đường thoát nước, mép gấp | Không cộng mái hai lần vào chiều cao; sửa chọn vỏ theo môi trường |
| Đế và bệ | Chiều cao riêng, cách neo, cửa kiểm tra, lối cáp | Không cộng bệ vào thân; không sao chép bệ sang cấu hình treo |
| Tai treo và móc cẩu | Vị trí thật, lỗ, vật liệu, liên kết, tải và tư thế nâng | Hình chiếu lặp không tạo thêm tai/móc; không suy tải nâng từ hình 3D |
| Bản lề | Model, trục, handedness, vùng quét, liên kết | Đếm theo nhóm vật lý; học sửa hướng mở đúng ngữ cảnh |
| Khóa và tay nắm | Model, lỗ khoét, offset mép, phần nhô trước/sau | Khi resize chỉ dịch chuyển theo anchor; giữ kích thước phần cứng |
| Tấm bịt và cửa cáp | Đường bao, chiều dày, lỗ, gland, hướng tuyến | Khả năng đưa cáp/cos qua và giữ yêu cầu bảo vệ |
| Vách phân khoang | Vùng ngăn, liên kết, khe xuyên và bảo vệ lỗ xuyên | Chứng minh form bằng tiêu chí; hai cánh không thay vách |
| MCCB và ACB | Đúng mã/cực, front/side, điểm gá, terminal, hành trình thao tác | Kiểm tra gá, lực đấu nối, cánh và khoảng dây; không suy adapter DIN theo dòng |
| Tay xoay và trục nối | Bộ phụ kiện tương thích, độ dài trục, mặt thao tác, lỗ khoét | Không tự thay tay gạt trực tiếp bằng tay xoay; học sửa phụ kiện có lý do |
| MCB RCCB RCBO | Bề rộng thật theo model/cực, ray tương thích, cọc và điều kiện ghép | Đặt liền chỉ khi điều kiện lắp/nhiệt cho phép; cực không phải số thân |
| Contactor và rơ le nhiệt | Kích thước cụm, vị trí ghép, hướng gá và vùng tháo | Cụm có thể cần envelope tổng; không đếm phụ kiện hai lần |
| Cầu chì và đế cầu chì | Số thân, model, mặt gá, vùng thay cầu chì | Hai đầu của một ký hiệu không thành hai cầu chì; giữ tiếp cận bảo trì |
| CT và đồng hồ đo | Tỷ số/loại, lỗ xuyên, hướng cực tính, đầu nối, mặt thao tác | CT vật lý khác bộ ba CT; cửa sổ CT phải chứa tuyến thanh/cáp thực |
| Đèn nút nhấn selector HMI | Mặt lắp, lỗ khoét đúng model, độ dày panel, block tiếp điểm sau cánh | Tách mặt hiển thị khỏi thân sau cánh; giữ vùng dây khi cánh mở |
| PLC nguồn timer và relay | Mã, mặt gá, khoảng nhiệt, terminal, vùng thay module | Không lấy SIDE làm FRONT; học bố trí theo luồng dây đã kiểm tra |
| VFD khởi động mềm và biến áp | Tải, tổn hao, hướng lắp, vùng tản nhiệt, khối lượng và đấu nối | Không bố trí chỉ bằng bbox; kiểm tra nhiệt và EMC trong phạm vi thiết kế |
| Thanh cái R S T N | Vật liệu, rộng/dày, tầng sâu, chiều dài, lỗ, tuyến, dòng và sự cố | Không nhận vật liệu từ màu; lượng đồng dựa hình học đã xác minh |
| Thanh PE và nối đất cánh | Tiết diện, đầu cốt, số điểm nối, liên kết khung và cánh | Không nối N với PE tùy tiện; không dùng thanh PE nhỏ cố định cho mọi tủ |
| Sứ và giá đỡ thanh cái | Model, khoảng đỡ, điểm gá, điện áp, chịu lực và sự cố | Có hình khối chưa chứng minh khả năng chịu ngắn mạch |
| DIN và máng dây | Tiết diện, chiều dài, điểm gá, tải, nắp và tỷ lệ lấp đầy | Không thêm máng nếu phương án không cần; phân biệt sẵn có với bổ sung |
| Cầu đấu và phụ kiện | Dòng/tiết diện dây, số cực, cầu nối, chặn, nhãn và vùng đi dây | Số vị trí đấu nối theo mạch; không suy tiếp địa thành cầu đấu |
| Cáp dây và đầu cos | Mã cáp, tiết diện, đường kính, bán kính uốn, chiều dài thẳng, hướng ra cọc | Kiểm tra tuyến 3D; học thay khoảng chừa từ lỗi cấn đã duyệt |
| Quạt lọc và chớp thoáng | Kích thước/lỗ, lưu lượng, tổn hao nhiệt, IP, vị trí hút/xả | Lỗ/mesh có nguồn chưa chứng minh đủ làm mát hoặc đạt IP |
| Nhãn và khung tên | Tên tủ/tag đã chốt, quan hệ BOM, đơn vị và tỷ lệ | Tag sinh mới phải phân biệt tag nguồn; không học tên khách hàng như đặc tính kỹ thuật |

Nguồn nghiệp vụ: [quy tắc chọn form](../QUY_TAC_CHON_FORM_VA_BO_TRI.md), [trình tự và ví dụ đo](../TRINH_TU_THIET_KE_VA_KHOANG_CACH.md), [giới hạn hình học 3D](../cabinet-solid-preview.md). Bảng trên là hợp đồng dữ liệu cần có; không tuyên bố tất cả trường đã tồn tại trong thư viện.

## Tài liệu tương ứng cần thu thập

| Nhóm tài liệu | Khóa ghép và vị trí bằng chứng | Trường được phép xác nhận |
| --- | --- | --- |
| Bản vẽ kích thước hãng | Hãng + mã + biến thể + phiên bản + trang | Kích thước ghi, phần nhô và hướng nhìn tương ứng |
| Hướng dẫn lắp đặt hãng | Mã + phụ kiện + điều kiện lắp | Lỗ gá, lỗ khoét, torque, vùng trống, tư thế lắp |
| Datasheet điện | Mã đặt hàng + cực + điện áp + phiên bản | Dòng, khả năng cắt, tổn hao và điều kiện định mức được công bố |
| Hồ sơ thiết kế cụm tủ | Cấu hình cụm + phiên bản + phạm vi xác minh | Kết cấu, phân khoang, điều kiện nhiệt/điện phù hợp phạm vi |
| CAD nguồn dự án | File hash + sheet + handle + mặt | Hình học và cấu hình đã thể hiện; chưa xác nhận mọi thông số model |
| Biên bản kiểm tra xưởng | Revision thiết kế + chi tiết + phép đo | Kết quả thực tế, lỗi chế tạo, thay đổi hoàn công |
| Ý kiến người dùng | Actor + revision + reason + trường đã sửa | Lựa chọn hoặc sở thích; chỉ thành nhãn kỹ thuật khi đủ căn cứ và được duyệt |

Không lấy brochure cùng họ sản phẩm để xác nhận lỗ khoét của mọi biến thể. Khi tải thêm tài liệu, lưu URL nguồn, ngày truy cập, phiên bản và hash bản lưu; ghi rõ tài liệu nào thay thế tài liệu nào. Giá và khuyến mại nằm ở nguồn báo giá riêng, không là bằng chứng tương thích kỹ thuật.

## Quy tắc đọc hồ sơ tự sinh

Trong [danh mục mẫu](DANH_MUC_MAU.md), một handle cho phép định vị lại chi tiết trong tệp gốc tương ứng. Handle chỉ có ý nghĩa cùng hash/file; không ghép handle trần giữa các tệp. Danh mục JSONL lưu các lần xuất hiện mà bố trí gốc đã nhận diện; hình học explode hoặc chưa phân loại vẫn cần rà soát. Không dùng danh sách INSERT để tuyên bố đã liệt kê đủ mọi chi tiết của mẫu.

`source_boundary_coverage_verified=true` là cờ của phép kiểm tra đường bao nguồn. Nó không thay `complete_semantic_review`, xác minh lỗ gá hoặc duyệt thiết kế. `route_candidates` là các nét ứng viên trong hệ nhiều hình chiếu; phải xác định mặt, vật liệu và nhóm vật lý trước khi đo lượng đồng.

## Ví dụ giải thích một quyết định bố trí

Một lý do đúng phải nêu: chi tiết nào, ràng buộc nào, bằng chứng nào và kết quả kiểm tra sau sửa. Ví dụ giả lập: “Dịch MCCB QF1 xuống 20 mm do envelope đầu cos cấn mái theo mặt SIDE; đầu vào lấy từ tài liệu model X, trang Y; sau dịch kiểm tra lại tuyến cáp và vùng MCB phía dưới”. Số 20 mm là thay đổi của tình huống đó; không trở thành quy tắc phải dịch mọi MCCB xuống 20 mm.

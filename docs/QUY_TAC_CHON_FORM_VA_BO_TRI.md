# Chọn form và bố trí tủ từ CatalogTB

## Đầu vào và nguồn hình học
- Giao diện gọi hãng là `brand`. Khi không có brand, hiển thị `Asian`; đây là nhãn mặc định, không phải bằng chứng nhà sản xuất. Thông tin web và hồ sơ hệ thống được đối chiếu riêng theo model, brand và thông số. Khớp model khác brand phải báo khác brand, không tự coi là đúng thiết bị hoặc đổi brand đã chốt.
- Chỉ sử dụng thiết bị trong `BE_AIDE/data/CatalogTB` và form trong `CatalogTB/Form tủ`.
- Bóc tách từng tủ, từng thiết bị vật lý và số lượng; tách thiết bị đi kèm thành vị trí lắp khi chúng có thân riêng. Không đếm timer/contactor hai lần giữa dòng chính và phụ kiện.
- Khi người dùng chọn cấu hình báo giá nguồn, ghép từng dòng với thiết bị sơ đồ trước khi đổi thông số. Giữ bằng chứng sơ đồ ban đầu, mã/hãng/số lượng báo giá và phần thêm mới. Không cộng hai BOM hoặc bỏ thiết bị chưa ghép. Giá trọn bộ tủ không phải đơn giá từng thiết bị.
- Lưu BOM sơ đồ và BOM thiết kế theo báo giá riêng. Chạy lại không thêm phụ kiện lần nữa. Chênh lệch đã được người dùng chọn theo báo giá là thay đổi được chấp nhận; vẫn phải kiểm tra hình học, đấu nối và tải của cấu hình mới.
- Nếu model chưa ghép được trong chỉ mục, kiểm tra file/block CAD nguồn và nhãn lân cận trước khi kết luận. `thiet_bi_can_ghep_model.json` là hồ sơ kiểm tra chưa hoàn tất, không phải thiết bị mới hoặc bằng chứng đã có CAD đúng mã. Không đổi tên block hãng khác để khớp báo giá.
- Hệ thống tự chọn CAD theo chức năng, loại thiết bị, hãng yêu cầu, số cực, model và tư thế lắp. Không yêu cầu người dùng chọn mặt CAD trong thẻ thiết bị.
- Lấy rộng/cao từ bao hình CAD theo mm; lấy sâu từ mặt bên cùng biến thể hoặc kích thước hồ sơ có nguồn. Không dùng khung trang, chữ chú thích hoặc mặt bên làm mặt trước. Kích thước hình học tham khảo không chứng minh dòng điện, khả năng cắt hoặc model chính xác.

## Chọn form theo bố trí thực tế
- Bố trí riêng từng tủ; ưu tiên form gốc phù hợp kiểu treo/đứng, trong/ngoài nhà, số cánh, bản lề và hướng dây vào.
- Thử bố trí thiết bị, rail, cọc đấu, đường dây/đồng và vùng thao tác trên các mặt trước khi chọn kích thước tủ. Chọn form nhỏ nhất đáp ứng bao hình và các vùng cần thiết; không chọn chỉ theo số lượng thiết bị.
- Kích thước vỏ trên sơ đồ là ràng buộc nguồn. Nếu không đủ chỗ, ghi rõ phần không phù hợp và đề xuất form lớn hơn; không âm thầm thay kích thước. Nếu báo giá và CAD gốc khác nhau, giữ riêng từng bằng chứng.
- Giữ hình học cơ khí nguồn, không co giãn thiết bị. Chỉ đổi kích thước form khi có quy tắc biến đổi hình học đã kiểm tra.
- Dành chỗ đi dây theo hướng đấu nối thực tế, bán kính uốn của dây đã chọn và yêu cầu nhà sản xuất. Không coi một khoảng cách mặc định là chuẩn cho mọi thiết bị.

## Các mặt và đường cấp điện
- Phân biệt cánh ngoài 1st, cánh trong 2nd, tấm lắp và mặt bên; lỗ khoét/E-VIEW phải cùng tâm với thiết bị thao tác.
- Với yêu cầu hiện tại, tay gạt MCCB tổng qua cánh trong 2nd, mở cánh ngoài để thao tác.
- RYB tương ứng RST. Cầu chì đèn đặt gần đường dây qua bản lề thực tế, có thể gần MCCB hoặc giữa cụm, nằm trong vùng hữu dụng và tránh vỏ/cánh khi đóng mở.
- MCB trên rail có thể đặt liền nhau theo bề rộng thật nếu nhà sản xuất cho phép. Không tự thêm khe hoặc máng khi phương án xương cá không cần.
- So sánh phương án dây lực và thanh đồng/xương cá theo đấu nối, dòng điện, chịu ngắn mạch, bảo trì và lượng đồng. Tối ưu số thanh và chiều dài nhưng không bỏ khoảng cách điện hay bảo vệ chạm trực tiếp.
- PE có thể là thanh đồng bố trí tương tự thanh cái. Không mặc định thanh tiếp địa nhỏ cho mọi tủ; kiểm tra tiết diện, chịu sự cố, số điểm nối và liên kết vỏ/cánh.

## Vòng kiểm tra bắt buộc
1. So BOM sơ đồ với báo giá và CAD gốc theo từng tủ, tag, loại, cực, thông số và số lượng; ghi chênh lệch có nguồn.
2. Kiểm tra CAD tạo ra: đủ thiết bị vật lý, đủ mặt, không thiếu nét, đúng hướng, đúng tâm thao tác/lỗ khoét, không chồng lấn, không vượt vùng lắp, đủ chiều sâu và đường dây.
3. Sửa nguyên nhân trong nhận diện, chọn CAD, chọn form hoặc bố trí; chạy lại và lưu kết quả từng vòng. Không đánh dấu đạt chỉ vì xuất được DXF.
4. Chỉ mở phần Báo giá sau thiết kế hoàn tất. Chỉ tạo Excel khi người dùng tải xuống. Thiếu mã hoặc giá thì giữ trạng thái chưa có giá, không tự đặt giá bằng 0.
5. Nếu nguồn còn mâu thuẫn hoặc chưa đủ dữ liệu xác minh, nêu chính xác mục chưa đạt; không tự chuyển thành kết quả đã duyệt.
# Đọc context và kiểm đếm PDF

PDF không có lớp text, hoặc lớp text chỉ có tiêu đề, phải đọc ảnh để tạo context. Context đọc được chưa xác nhận danh mục thiết bị đầy đủ.

Kiểm đếm độc lập giữ đúng mã tủ, đếm từng thân thiết bị, gồm nhánh dự phòng có ký hiệu nhưng thiếu thông số. Không gom đèn, đồng hồ và cầu chì thành một OTHER; không suy tiếp địa thành cầu đấu. Chuẩn hóa tên loại tương đương có căn cứ (LIGHT/Đèn báo, METER có tên Vôn kế, SWITCH có tên chuyển mạch chọn điện áp); không tự đổi CB chung thành MCB hoặc đồng hồ chưa rõ thành vôn kế.

Lỗi OCR và lỗi đối chiếu danh mục phải hiển thị riêng với lỗi CatalogTB. Thiết bị thiếu hoặc bị suy diễn vẫn chặn tạo thiết kế và báo giá.


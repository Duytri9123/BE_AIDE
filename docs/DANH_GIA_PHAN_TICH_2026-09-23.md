# Đánh giá phân tích thiết bị và xuất CAD/báo giá

Ngày 23/09/2026. Phạm vi: mã nguồn backend, luồng hiển thị vùng ảnh frontend, dữ liệu SQLite hiện có, ảnh nguồn và kiểm thử offline. Không gọi lại nhà cung cấp AI, không thay kết quả phân tích trong cơ sở dữ liệu, không chạy luồng đăng nhập/giao diện end-to-end.

## Kết luận thực tế

Hệ thống có nền tảng để hỗ trợ bóc tách và lập dự toán có người kiểm tra. Chưa đủ bằng chứng để coi là quy trình tự động phát hành CAD/báo giá chính xác hoàn toàn. Điểm yếu nổi bật là độ đúng của vùng ảnh, tách thành phần trong cụm thiết bị và cách công bố trạng thái/giá còn thiếu.

Không đưa ra phần trăm chính xác: cơ sở dữ liệu hiện chỉ có một iteration với 34 dòng thiết bị của một tủ; chưa có danh sách chuẩn đã được người dùng duyệt để tính sai/thiếu/thừa trên tập đại diện.

## Bằng chứng trên dữ liệu hiện có

- Iteration 1: 34/34 dòng có box, ảnh cắt và tên nguồn. Các dòng loại MCB/MCCB/ACB đều có Icu trong dữ liệu. Đây là độ đầy đủ trường, không chứng minh thông số đúng.
- Nguồn `storage/projects/1/nguon.jpg`: ảnh 1000 × 777 pixel, 28 nhánh M1–M28 và cụm đầu vào/đo lường.
- M1 lưu box `[323,137,368,163]`, tương ứng x=137..163, y≈251..286 pixel. Đối chiếu ảnh gốc: ký hiệu/nhãn đóng cắt nằm phía trên, nên box chạm vùng dưới ký hiệu và phần dây. Ảnh cắt có padding vẫn thấy nhiều nhánh lân cận; không thể coi crop này là chứng minh định vị chính xác một thiết bị.
- PA/PV đang là các dòng gộp đồng hồ và chuyển mạch AS/VS. Cần chốt là mua theo bộ hay tách vật tư trước khi đánh giá đủ BOM.
- FU1 đang có quantity=1; không có bộ dữ liệu chuẩn để kết luận tự động phải là 1 hay 3. Cần đối chiếu cách biểu diễn mạch và phạm vi vật tư.
- Hai file dự án được đăng ký hiện là nguồn JPG và bảng ký hiệu DWG; chưa có bản ghi file xuất hiện hành để khẳng định người dùng đã nhận được CAD/báo giá.

## Lỗi đã sửa trong lượt kiểm tra

| Vấn đề | Tác động | Sửa đổi |
|---|---|---|
| Excel đa tủ: tủ cuối tham chiếu tổng bảng, tổng bảng bao dòng tủ cuối | Vòng lặp công thức, tổng tiền không đáng tin | Tính subtotal riêng từng tủ; tổng bảng chỉ cộng các tủ; xử lý bảng rỗng |
| Ghép xác minh box bằng tag/tên | QF1 của các tủ khác nhau có thể nhận cùng vùng | ID riêng cho từng phần tử; từ chối ID trùng/thiếu và box không hợp lệ |
| Quy tắc cầu chì ghi đè lượng x6 | Sai số lượng mua | Số lượng ghi rõ được ưu tiên trước quy tắc suy luận |
| Khóa gộp bỏ panel_code và Icu | Có thể gộp thiết bị khác tủ/khả năng cắt | Bổ sung hai thuộc tính vào khóa gộp |
| Hai dict thiếu quantity không ghi lại tổng | Mất số lượng sau gộp | Luôn ghi quantity tổng |
| Chuẩn hóa đầu vào bước tạo CAD bỏ metadata nguồn/box/số lượng | Kết quả lưu lại mất khả năng truy nguồn | Bảo toàn các trường này khi chuyển sang schema |

## Các điểm chưa khép kín

| Mức ưu tiên | Phát hiện từ mã nguồn | Việc cần hoàn thiện |
|---|---|---|
| Cao | Bước xuất Excel bắt exception và tiếp tục trả `success=True` | Trả trạng thái thành công một phần/lỗi; chỉ công bố hoàn tất khi đủ file |
| Cao | Dọn CAD cũ theo tiền tố BanVe_/PhacThao_ trước khi toàn bộ quy trình hoàn tất | Chỉ dọn file `is_generated`, sau khi xuất/publish thành công; bảo vệ tệp nguồn |
| Cao | Nhánh PDF có bước verifier; ảnh thường chưa có cùng cơ chế xác minh độc lập | Áp dụng thống nhất và đo kết quả trên ảnh thật; bản sửa ID chưa tự sửa tọa độ cũ |
| Cao | Suy luận cầu chì dùng ngữ cảnh toàn tủ và có thể nâng confidence | Ràng buộc đúng mạch; lưu rõ trạng thái suy luận, không dùng như xác nhận từ nguồn |
| Vừa | CAD chọn text khớp nhất, chưa giải quyết triệt để tag lặp trong nhiều tủ | Phân vùng tủ trước khi khớp; từ chối vị trí mơ hồ |
| Vừa | Giá không tìm thấy trả 0; fallback giá có thể là ước tính | Hiển thị trạng thái/nguồn giá và mức độ hoàn thiện báo giá |
| Vừa | Excel có câu cam kết bảo toàn 100% SLD/chọn lọc bảo vệ | Chỉ hiển thị kết luận phù hợp với kiểm tra đã thực hiện |
| Vừa | Kích thước/khả năng lắp vừa chưa bao phủ mọi yêu cầu thiết kế thực tế | Xác minh catalog, nhiệt, khoảng cách lắp và bảo trì theo hồ sơ cụ thể |

Đây là các phát hiện review cần xử lý tiếp, không phải các tính năng đã hoàn tất trong lượt sửa này. Quy tắc đầy đủ nằm trong `QUY_TAC_PHAN_TICH_THIET_BI.md`.

## Kiểm chứng đã chạy

- 7 kiểm thử có sẵn: gộp phụ kiện, BOM DXF không mất dòng, nhiều phần của cùng tủ, kích thước/layout theo catalog và khung quá nhỏ.
- 10 kiểm thử bổ sung: số lượng ghi rõ; tính lặp 3XCT; box với tag trùng; verifier lỗi/mơ hồ; crop trong biên ảnh; gộp theo tủ/Icu; quantity mặc định; Excel đa tủ; Excel rỗng; bảo toàn metadata khi chuẩn hóa đầu vào tạo CAD/báo giá.
- Mẫu Excel đa tủ: tủ 1 có hai bộ × (3×100 + 1×50) = 700; tủ 2 = 2×200 = 400; trước thuế 1.100; thuế kiểm thử 10% = 110; tổng 1.210. Bộ kiểm thử đọc lại file và tính chuỗi công thức, phát hiện vòng lặp. Thuế 10% chỉ là dữ liệu kiểm thử.
- Tạo DXF bằng generator thực từ 34 dòng đã lưu trong thư mục thử riêng `tmp/audit_20260923/1/`; đọc lại được bằng ezdxf, 967 entities, 0 lỗi và 0 sửa chữa cấu trúc.
- Chưa mở CAD trong AutoCAD để kiểm tra trực quan toàn bộ hình chiếu; chưa tính lại workbook bằng Microsoft Excel; kiểm tra cấu trúc/công thức không thay thế hai bước đó.
- Không chạy lại AI nên chưa chứng minh recall/precision của nhà cung cấp hiện hành và chưa cải thiện dữ liệu cũ trong DB.

## Thứ tự nghiệm thu đề xuất

1. Chốt BOM đúng của ảnh hiện có và sửa vùng minh chứng sai, đặc biệt nhóm nhánh M1–M28 và cụm PA/PV/FU1.
2. Khép kín trạng thái lỗi xuất file và giao dịch công bố CAD/Excel; kiểm thử lỗi ghi file có chủ đích.
3. Đối soát BOM giữa ảnh, bảng thiết bị, CAD và Excel; kiểm tra bằng phần mềm đích.
4. Mở rộng bộ mẫu nhiều tủ/nhiều trang/tag trùng rồi đo độ chính xác thay vì dùng confidence tự báo.

# Quy trình thiết kế tủ từ yêu cầu và hình học có nguồn

## Thu thập yêu cầu trước khi bố trí

Hồ sơ mỗi tủ cần có mã tủ trong dự án, sơ đồ nguyên lý, BOM đọc từ nguồn, BOM đã chọn cho thiết kế, môi trường lắp, kiểu treo/đứng, hướng cáp vào/ra, số lớp cánh, kích thước bắt buộc và form phân khoang yêu cầu. Thu thập tải, điện áp, dòng, ngắn mạch, điều kiện nhiệt, IP/IK và yêu cầu bảo trì theo phạm vi dự án. Trường chưa biết để `null` cùng nguyên nhân và tác động; không thay bằng giá trị mặc định rồi coi là đã xác nhận.

Tách ràng buộc do khách hàng chốt khỏi phương án AI đề xuất. Ví dụ kích thước H700 W500 D250 từ bản vẽ là đầu vào nguồn; đổi thành H900 W600 D250 là đề xuất mới cần ghi chênh lệch. Tủ treo không tự trở thành tủ đứng vì mẫu CAD có bệ.

## Phân loại form và kiểu vỏ

Vỏ tủ quyết định kết cấu, mặt lắp, cánh, hèm, mái và đế. Form phân khoang quyết định quan hệ tách giữa thanh cái, đơn vị chức năng và đầu nối. Lấy form yêu cầu từ hồ sơ dự án; chứng minh form thực tế bằng quan sát và kiểm tra theo phiên bản áp dụng. Không suy form từ kích thước, dòng CB, số cửa hoặc việc nhìn thấy máng dây.

Catalog hiện lưu bảy mã form. Với 2a/3a, điều kiện đầu nối không cần tách khỏi thanh cái phải được biểu diễn như điều kiện không bắt buộc, không biến thành yêu cầu bắt buộc phải nối chung khoang. Khi tiêu chí chưa quan sát được, giữ `unknown`; không thấy vách trong một mặt CAD cũng chưa đủ kết luận Form 1. Xem [đánh giá cách lưu tiêu chí hiện tại](03_DANH_GIA_HIEN_TRANG.md).

| Form | Quan hệ phân khoang để đối chiếu |
| --- | --- |
| 1 | Không phân khoang nội bộ |
| 2a | Thanh cái tách đơn vị chức năng; không bắt buộc tách đầu nối khỏi thanh cái |
| 2b | Như 2a, đầu nối tách thanh cái |
| 3a | Thanh cái và từng đơn vị chức năng tách nhau; đầu nối/cáp ngoài tách đơn vị chức năng, có thể chung vùng đầu nối |
| 3b | Như 3a, đầu nối tách thanh cái |
| 4a | Tách từng đơn vị và đầu nối liên quan khỏi nhóm khác; đầu nối trong khoang đơn vị tương ứng |
| 4b | Như 4a, đầu nối từng nhóm nằm trong khoang bảo vệ riêng ngoài khoang đơn vị |

Đối chiếu bảng với [ABB workbook, trang in 51, trang PDF 53](https://library.e.abb.com/public/32f98df19e5849e1b6b5d6172e00be73/2CPC000313B0201.pdf) và [ABB Technical Application Papers 11, mục 6](https://library.e.abb.com/public/851c5f31e1c142e89adc271788b45bbb/1SDC007110G0203.pdf). Đây là tóm tắt quan hệ để lập hồ sơ, không bao trùm các điều kiện bảo vệ hoặc phép xác minh của cụm tủ. Chọn phiên bản tiêu chuẩn áp dụng theo dự án; không dùng tài liệu diễn giải cũ thay toàn bộ IEC 61439-2:2020.

## Quy trình thiết kế

1. **Đọc sơ đồ và kiểm đếm độc lập.** Định danh bằng project, tủ và occurrence ID; giữ tag nguồn. Bóc đúng loại, cực, dòng, model, chức năng và số lượng. Khung tên, bảng ký hiệu và hình chiếu lặp không tạo thiết bị vật lý mới.
2. **Đối soát cấu hình thiết kế.** So từng dòng sơ đồ với lựa chọn báo giá/thay thế. Giữ BOM nguồn riêng; lưu thay đổi được chấp nhận và phụ kiện cần thiết. Chạy lại không được thêm phụ kiện lần nữa.
3. **Chọn CAD có bằng chứng.** Khớp chức năng, hãng, model/biến thể, số cực và hướng lắp. Ghép front/side/operator của cùng biến thể; thiếu mặt hoặc chiều sâu thì giữ lỗi cụ thể. Nhãn `Asian` không xác nhận nhà sản xuất.
4. **Lập các chi tiết vật lý.** Tách thân, tay thao tác, phụ kiện gá, cầu đấu, rail, máng, thanh cái, cách điện và dây liên kết cánh. Nêu cấu kiện nào có sẵn trên vỏ, cấu kiện nào cần bổ sung; tránh mua hoặc đếm hai lần.
5. **Đặt tuyến kết nối và mặt lắp.** Chọn hướng cáp vào/ra, đường thanh cái/dây và vùng bảo trì. Thân MCCB ở tấm/đố gá; tay thao tác có thể qua cánh trong theo hồ sơ. Đèn, đồng hồ, HMI phải có mặt sở hữu theo dự án/model.
6. **Tính không gian cần thiết.** Dùng bao hình, mốc gá, đầu cọc/cos, vùng uốn cáp, nhô sau cánh, quỹ đạo bản lề và vùng nhiệt. Kiểm tra trong hệ mặt và chiều sâu thực, không chỉ tổng diện tích hình chữ nhật.
7. **Thử các mẫu vỏ hợp lệ.** Lọc môi trường, kiểu lắp, cánh, form và độ tin cậy trước; xếp hạng kích thước sau. Ưu tiên mẫu nhỏ nhất đáp ứng đầy đủ ràng buộc. Nếu chưa có mẫu đủ dữ liệu, trả phương án tham khảo kèm mục thiếu.
8. **Đổi kích thước có kiểm soát.** Chỉ đổi chiều được hỗ trợ, giữ kích thước thiết bị, lỗ và phụ kiện cơ khí; đồng bộ các mặt và DIM. Kiểm tra lại cấu kiện khi kích thước thay đổi.
9. **Kiểm tra và duyệt theo phạm vi.** So lại thiết bị, số lượng, mặt, tọa độ, mốc gá, đấu nối và va chạm; ghi pass/fail/unknown cho từng phép kiểm tra. Hình 3D đẹp hoặc xuất DXF thành công chưa đủ để duyệt chế tạo.
10. **Lưu phiên bản và kết quả.** Lưu đầu vào, phương án AI, phương án sau sửa, lý do, người duyệt, bằng chứng và kết quả chế tạo nếu có. Chỉ mở luồng báo giá hoàn tất khi thiết kế đạt yêu cầu của luồng đó; CAD nháp/báo giá nháp vẫn phải giữ trạng thái nháp.

Nguồn quy trình: [chọn form](../QUY_TAC_CHON_FORM_VA_BO_TRI.md), [trình tự thiết kế](../TRINH_TU_THIET_KE_VA_KHOANG_CACH.md), [phân tích thiết bị](../QUY_TAC_PHAN_TICH_THIET_BI.md).

## Hệ tọa độ và bằng chứng kích thước

Mỗi mặt có ID ổn định, phép đổi từ `cad_world` sang hệ cục bộ theo mm, đường bao hữu dụng và vật cản. Đề xuất hệ cục bộ: nhìn trực diện mặt gá, X sang phải, Y lên trên; chiều sâu Z tính từ sau tủ ra trước. Đây là quy ước tích hợp cần ánh xạ rõ với hệ hiện có, không áp ngầm lên tọa độ nguồn.

Mốc `rebate`, `mounting_plane`, `inner_door_plane` lưu khoảng sâu từ mặt sau, handle nguồn và trạng thái xác minh. Chưa rõ mốc gá thì không lấy mặt sau bao hình làm mốc gá. Cánh chuyển động cần trục bản lề, chiều mở, giới hạn góc và vật cản; trạng thái đóng vừa không chứng minh mở được.

Đối với block `formtu`, metadata hiện ghi inch nhưng thiếu kích thước mm đã xác minh. Giữ kích thước thô, đơn vị file, tỷ lệ INSERT lồng nhau và DIM mẫu riêng; đối chiếu kích thước thực trước khi thiết lập phép đổi. Không tự nhân 25,4 cho toàn thư viện chỉ vì header inch, cũng không mặc định 25 nghĩa là 25 mm.

## Phân cấp quy tắc

| Loại | Căn cứ | Cách dùng |
| --- | --- | --- |
| Yêu cầu dự án | Hồ sơ và lựa chọn người dùng có phiên bản | Chặn phương án không đáp ứng; thay đổi phải lưu lý do |
| Giới hạn kỹ thuật áp dụng | Tài liệu đúng model, điều kiện vận hành và tiêu chuẩn áp dụng | Ràng buộc bắt buộc, không để điểm học ghi đè |
| Chính sách bố trí của người dùng | `fishbone_rstn.json` và quy tắc dự án | Điểm xuất phát trong đúng phạm vi; chưa thay xác minh kỹ thuật |
| Khoảng đo ở CAD cũ | Handle, mặt và tệp có hash | Ví dụ hình học; không tự thành khoảng cách tối thiểu chung |
| Sở thích đã học | Các chỉnh sửa đã duyệt cùng ngữ cảnh | Xếp hạng giữa các phương án hợp lệ |

Nếu hai yêu cầu bắt buộc mâu thuẫn, giữ trạng thái chưa giải quyết và chỉ rõ hai nguồn. Tài liệu hãng phải khớp biến thể; tài liệu mới hơn không tự phù hợp với thiết bị cũ. Bằng chứng thu hồi phải làm mất hiệu lực kết quả phụ thuộc.

## Chính sách khoảng cách đang có

`data/design_rules/fishbone_rstn.json` và `app/services/cad/design_policy.py` hiện đặt khoảng nóc ban đầu d1=150 mm cho 100≤In<200 A, d2=250 mm cho 200≤In<300 A, d3=400 mm cho In≥300 A. Biên bên là 150 mm khi In>200 A và 110 mm khi In≤200 A. Quy tắc xương cá hiện chặn CB tổng >250 A. Đây là quy tắc dự án, không phải giới hạn dòng điện chung cho mọi hệ phân phối.

Với tuyến uốn 90° có đủ dữ liệu, công thức dự trữ đang dùng là:

```text
S = bán kính uốn trong + đường kính ngoài cáp + đoạn thẳng đầu cos
    + độ lệch cọc so với mốc thân + khoảng thao tác lắp đặt
Khoảng nóc đề xuất = max(khoảng ban đầu theo dòng, S)
```

Chỉ dùng công thức này cho hình học và hướng ra cọc phù hợp. Góc khác, cáp nhiều lõi có giáp hoặc tuyến xuyên vật cản cần mô hình tuyến tương ứng. Thiếu mã cáp/tài liệu bán kính uốn thì kết quả vẫn tạm tính. Không dùng pitch 30 mm của tuyến minh họa làm chứng nhận cách điện hay chịu ngắn mạch.

## Đầu ra tối thiểu của mỗi phương án

Hồ sơ cần có revision, fingerprint nguồn và catalog, yêu cầu đã chốt, BOM nguồn/BOM thiết kế, mẫu vỏ/biến đổi, chi tiết vật lý, quan hệ thân–tay thao tác–gá, bảng tọa độ theo mặt, tuyến kết nối, bằng chứng và kết quả kiểm tra. Trạng thái đề xuất gồm `draft`, `needs_evidence`, `reviewed_layout`, `engineering_approved`, `fabrication_released`; đây là mô hình trạng thái cần triển khai, chưa phải API hiện tại.

Mỗi kiểm tra lưu `status=pass|fail|unknown|not_applicable`, phương pháp, đầu vào, nguồn, người/công cụ kiểm tra và phiên bản. `not_applicable` phải có lý do được duyệt; không chuyển thiếu dữ liệu thành không áp dụng. Chỉ trạng thái cuối cùng có người có thẩm quyền và các kiểm tra áp dụng đã đạt mới được phát hành chế tạo.

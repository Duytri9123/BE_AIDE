# Kiểm tra thư mục ABB, LS và CHINT — 21/10/2026

**Cập nhật sau kiểm tra:** hai mặt ABB chưa xác định đã được cách ly và chặn đường dẫn cũ; 18 DXF có lỗi metadata đã được làm sạch và kiểm chứng hình học không thay đổi. Các số liệu bên dưới là kết quả phát hiện trước khi sửa. Xem [kết quả xử lý mới nhất](../catalog-error-repair-2026-10-21/README.md).

Đã dựng lại dữ liệu thư viện trực tiếp từ hồ sơ trên đĩa, không chỉ dùng bản chỉ mục cũ. Phạm vi gồm 416 hồ sơ nguồn của ba hãng và các hồ sơ được gán hãng tương ứng trong thư mục chung; 395 mục đang hiển thị. Có 12 hồ sơ nguồn đã ẩn. Không sửa, xóa hay công bố lại CAD trong đợt kiểm tra này.

## Kết quả về mặt CAD

| Hãng | Mục hiển thị | Tham chiếu mặt | Chỉ một mặt | Chưa có bộ đủ sáu hướng cùng biến thể |
|---|---:|---:|---:|---:|
| ABB | 94 | 246 | 3 | 94 |
| LS Electric | 264 | 1.009 | 61 | 153 |
| CHINT | 37 | 79 | 18 | 32 |

Tổng cộng còn 279 mục chưa có bộ đủ sáu hướng; 82 mục chỉ một mặt. Một mặt bên chung không được tính thành cả trái và phải; các biến thể khác nhau không được ghép thành một bộ. Đây là kiểm tra độ phủ sáu hướng theo yêu cầu, không có nghĩa tất cả phụ kiện đều bắt buộc sáu hình chiếu để sử dụng. Có số đo 2D không chứng minh đã đủ mặt hoặc đủ kích thước cơ khí để gia công.

Ba nhóm contactor LS MC-9/12/18/25/32, MC-35/40/50/63 và MC-65/75/85/95 có 6–7 tệp nhưng vẫn thiếu hướng: nhiều tệp là mặt sau hoặc thuộc biến thể khác nhau.

Danh sách từng thiết bị và mặt thiếu: [missing-views.csv](missing-views.csv).

## Nhận diện còn cần xử lý

- ABB ZCT-300A, hồ sơ `BienDong/ABB/ZCT-300A/thong_tin_thiet_bi.json`: hai mặt `A02_abb-V002`, `A02_abb-V003` vẫn có nhãn **CAD cần đối chiếu thiết bị**. V001 là hình vòng xuyên dây; V002 là thân chữ nhật có nhiều đầu cực, V003 có biên dạng thân lắp ray. Qua kiểm tra hình ảnh, không đủ bằng chứng coi V002/V003 là các góc nhìn của vòng ZCT trong V001. Không đổi tên chúng thành mặt bên/mặt sau để làm đủ bộ. Cần tách khỏi mục ZCT hoặc xác minh và gán lại đúng thiết bị. [Ảnh đối chiếu ba mặt](abb-zct-review.png).
- Danh sách hiển thị LS/CHINT không còn nhãn mặt chưa xác định.
- Có **55 mục cần rà soát thông tin nhận diện**: ABB 2, LS 41, CHINT 12. Tiêu chí là trạng thái hãng chưa được xác minh, thiếu mã/họ trong trường mã chính, hoặc là bản tham khảo/cụm. Đây là danh sách cần kiểm tra, không phải kết luận 55 mục bị nhận diện sai. Không suy mã đặt hàng, dòng cắt, điện áp cuộn hút hoặc số cực từ hình dáng.
- Ví dụ còn thiếu mã chính: biến tần LS, một số CAD nguồn LS theo khung AF, biến áp điều khiển CHINT, các CAD CHINT NXM-250/320 và NXM-400/630 dạng tham khảo. Các mặt NXM chính hãng đã nhập có hồ sơ riêng; không đồng nhất với các CAD nguồn cũ.

Chi tiết: [identity-review.csv](identity-review.csv), [issues.json](issues.json).

## Tệp và dữ liệu kỹ thuật

- Đọc và kiểm tra 1.340 tệp DXF riêng biệt được hồ sơ tham chiếu: tất cả đọc được, đơn vị hiệu lực mm, không có lỗi audit còn tồn tại hoặc hình rỗng. Không thiếu DXF/ảnh SVG được khai báo; SVG kiểm tra được cú pháp XML. Kiểm tra cú pháp không chứng nhận chất lượng hình ảnh của mọi SVG.
- 18 DXF có sửa chữa trong bộ nhớ khi audit: 3 tệp LS Metasol có khóa DICTIONARY không hợp lệ; 15 tệp mẫu có tham chiếu kiểu chữ MLEADERSTYLE không hợp lệ. Không thấy lỗi hình học không thể đọc. Chưa lưu các sửa chữa này vào nguồn. [Chi tiết](dxf-in-memory-fixes.json).
- 11 tệp `CadDon/ban_ve.dxf` trong LS không còn được hồ sơ tham chiếu; cả 11 thuộc hồ sơ **đã ẩn**, không phải thiết bị đang hiển thị bị quên thêm CAD. Đã kiểm tra thêm 11 tệp này: mở được, không có lỗi audit. Chúng gồm các block HCN BKN, abn203c-4, ABN53c-4, abs103-4, ABS(N)803-3, hai block TS1600 và MT-63. Chưa khẳng định hướng nhìn hoặc mã thiết bị của các bản này. [Danh sách](unreferenced-cad-validation.json).
- Không có hồ sơ nguồn đang hoạt động thuộc phạm vi kiểm tra mà hoàn toàn không khai báo CAD. Nhưng vẫn còn nhiều dòng bảng giá chưa có liên kết CAD được xác minh.
- Dữ liệu dựng lại khớp tập thiết bị và tập mặt đang có trong chỉ mục. Không có mục nào mất toàn bộ số đo CAD đã bổ sung.

## Đối chiếu bảng giá

| Hãng | Dòng bảng giá | Có liên kết họ CAD sáu hướng | Liên kết CAD còn thiếu hướng | Chưa có liên kết CAD tường minh |
|---|---:|---:|---:|---:|
| ABB | 4.446 | 0 | 311 | 4.135 |
| LS Electric | 517 | 336 | 43 | 138 |
| CHINT | 1.505 | 11 | 380 | 1.114 |

Đếm từ `supplier_pricebooks.json` theo ID dòng giá được ghi trong hồ sơ CAD, đúng hãng. **Chưa có liên kết tường minh không đồng nghĩa chắc chắn không có CAD liên quan**; có thể còn thiếu ánh xạ họ/mã. Liên kết họ CAD cũng không xác nhận tất cả mã cùng kích thước, đầu cực, cuộn hút hoặc dòng cắt.

Riêng LS, phần chưa liên kết gồm 74 phụ kiện, 32 MCB, 15 SPD, 6 ELCB, 5 contactor, 2 MCCB, 2 đồng hồ và 2 RCBO. Ưu tiên đối chiếu mã bảng giá với các CAD BKN/BKD đã có trước khi kết luận thiếu hình.

[Danh sách dòng giá chưa liên kết](pricebook-without-explicit-cad.csv), [toàn bộ liên kết](pricebook-coverage.json).

## CAD ngoài đã tải nhưng chưa nhập

Theo kiểm kê nguồn CHINT hiện có, còn 10 liên kết tệp đã tải nhưng chờ đối chiếu; gồm NXM-125S, NXM-250S 2P, NM8N-125/250 và NXM-400/630. Một số mô hình có chi tiết rời hoặc bao hình không khớp thân catalogue; không cắt bỏ tùy ý để đưa vào thư viện. 203 liên kết mới được tìm thấy, chưa tải, không được tính là CAD đã bổ sung. Đây là trạng thái từ tệp kiểm kê nguồn lưu trên đĩa, không phải kết quả tìm web mới trong lần kiểm tra này.

Nguồn chi tiết: [kiểm kê CHINT](../chint-research-2026-10-21/summary.json).

## Thứ tự xử lý đề xuất từ kết quả kiểm tra

1. Xác minh/tách hai mặt ABB đang gắn vào ZCT-300A; rà lại phân loại ZCT so với CT trong hồ sơ.
2. Đối chiếu 55 mục thiếu thông tin nhận diện; chỉ giữ thông số đã có bằng chứng.
3. Bổ sung đúng các hướng còn thiếu cho cùng biến thể, ưu tiên 79 mục LS/CHINT chỉ một mặt.
4. Hoàn thiện ánh xạ dòng giá với họ CAD đúng kích thước/số cực; không dùng một dòng cắt chung cho các mã khác cấp khả năng cắt.
5. Làm sạch 18 lỗi tham chiếu metadata DXF với bản sao kiểm chứng hình học; giữ các bản nguồn chưa xác định ngoài danh sách sử dụng.

Số liệu máy đọc: [summary.json](summary.json), [từng mục](items.json), [từng hồ sơ](profiles.json), [từng DXF](dxf-files.json).

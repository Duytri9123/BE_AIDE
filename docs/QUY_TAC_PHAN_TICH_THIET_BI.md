# Quy tắc phân tích thiết bị, vùng ảnh, CAD và báo giá

Phiên bản 1.0 — 23/09/2026. Đây là hợp đồng nghiệp vụ và tiêu chí nghiệm thu của AIDE; các mục chưa triển khai được ghi riêng trong báo cáo đánh giá. Tài liệu không phải chứng nhận thiết kế điện hoặc tiêu chuẩn IEC.

## 1. Nguồn và phạm vi

- Phân loại từng tệp: bản vẽ nguồn, bảng ký hiệu, catalog, tài liệu tham chiếu, kết quả hệ thống sinh ra. Không bóc số lượng từ bảng ký hiệu hoặc CAD đã sinh như thiết bị của dự án.
- Mỗi thiết bị phải truy về tệp, trang (đánh số từ 1 khi có trang), tủ và vị trí/nhãn. Chưa xác định thì để trống và yêu cầu đối chiếu; không dựng bằng chứng.
- Danh tính thiết bị gồm nguồn, trang, tủ, nhãn và vị trí xuất hiện. Tag QF1 không duy nhất trên toàn dự án.
- Giữ riêng dữ liệu đọc từ nguồn, thiết bị đề xuất thay thế và vật tư suy luận bổ sung.

## 2. Bóc tách và số lượng

- Ghi loại, tên, thông số, số cực, dòng định mức, khả năng cắt, tag, tủ, số lượng và quan hệ cấp nguồn khi nguồn thể hiện. Không lấy dòng định mức lớn nhất làm bằng chứng duy nhất cho thiết bị đầu vào.
- Thiếu hoặc mờ thông số phải ghi chưa xác định. Điểm confidence của mô hình không phải độ chính xác đã đo.
- `drawing_quantity`: số lượng/ký hiệu đọc từ bản vẽ; `procurement_quantity`: số lượng vật tư theo quy tắc đã xác nhận; `quantity_basis`: căn cứ. `quantity` dùng để xuất phải thống nhất với lựa chọn nghiệp vụ đã duyệt.
- Số lượng ghi rõ có ưu tiên cao hơn suy luận theo mạch. Không ghi đè x6 thành 3 vì mạch ba pha.
- 3P là số cực, không phải ba thiết bị. 3XCT là cụm ba biến dòng; xử lý lặp không được tăng thành 9.
- Một nhóm “3 x MCB 1P” phải được phân biệt với “MCB 3P”; nếu chưa đọc rõ thì giữ trạng thái cần kiểm tra.
- Không tự tăng cầu chì đo lường thành ba chỉ vì trong cùng tủ có CT/đèn ba pha. Cần bằng chứng thuộc đúng mạch và ghi rõ suy luận.
- Đồng hồ và bộ chuyển mạch là các thành phần cần đối chiếu riêng. Có thể báo giá theo bộ nếu xác định được thành phần, mã và phạm vi bộ.
- Phụ kiện có quan hệ cha–con và căn cứ số lượng. Quy ước hiện tại của danh sách `accompanying_accessories` là tổng số phụ kiện của dòng cha; không nhân thêm lần nữa khi gộp.
- Chỉ gộp dòng mua sắm khi cùng tủ, loại, thông số, mã, hãng, số cực, dòng, Icu và giá. Không dùng gộp mua sắm để xóa danh tính/quan hệ nối dây của từng thiết bị.

## 3. Vùng ảnh và minh chứng

- `box_2d = [ymin, xmin, ymax, xmax]`, chuẩn hóa 0..1000 trên đúng ảnh đầu vào; gốc trên trái. Phải có xmin < xmax và ymin < ymax.
- Chuyển sang pixel: x = giá trị x × chiều rộng / 1000; y = giá trị y × chiều cao / 1000. Không dùng chiều rộng để tính y.
- Box phải chứa ký hiệu và nhãn của chính thiết bị. Ảnh cắt có thể thêm ngữ cảnh, nhưng phần thêm không chứng minh box chính xác.
- Khi xoay/cắt ảnh trước phân tích, phải lưu phép biến đổi để hiển thị lại đúng hệ tọa độ.
- Xác minh lần hai dùng ID của từng phần tử, kèm tủ/tag/thông số. Không ghép kết quả bằng tag lặp. ID trùng, thiếu, box rỗng hoặc xác minh thất bại → chưa có vùng được xác minh.
- CAD dùng `cad_world` với tọa độ thật. Vùng quanh text chỉ là vị trí nhãn, không được khẳng định là biên thiết bị. Nhiều nhãn giống nhau cần phân giải theo tủ/vị trí trước khi chấp nhận.
- Lưu và phục hồi kết quả phải giữ nguồn, box, ảnh tổng, ảnh cắt và căn cứ số lượng xuyên suốt bước tạo CAD/báo giá.

## 4. Tạo CAD

- CAD bố trí tủ được sinh từ dữ liệu đã kiểm tra; không đồng nghĩa với bản vẽ hoàn công hoặc sơ đồ đấu nối đầy đủ.
- BOM trên CAD và báo giá phải đối soát theo tủ, thiết bị, phụ kiện và số lượng; không giới hạn số dòng làm mất thiết bị cuối bảng.
- Ưu tiên kích thước được chỉ định nhưng phải báo khi không đủ chỗ. Kích thước catalog và kích thước ước tính phải phân biệt được.
- Kiểm tra va chạm, khoảng lắp đặt, cửa, vị trí cáp và không gian bảo trì. Dữ liệu chưa có thì ghi rõ, không tuyên bố đã đạt.
- DXF phải ghi được, đọc lại được, qua kiểm tra cấu trúc; cần kiểm tra trực quan riêng về chồng chữ, cắt bảng và vị trí hình chiếu.
- Sinh file vào đường dẫn mới; chỉ thay phiên bản chính khi các đầu ra bắt buộc thành công. Không xóa tệp nguồn theo tiền tố tên file.

## 5. Báo giá

- Ghi rõ đơn vị của từng dòng. Ba CT vật lý không tự động được hiểu là ba “bộ CT ba pha”.
- Thành tiền dòng = số lượng × đơn giá. Đơn giá tủ = tổng chi tiết của một tủ. Thành tiền tủ = số tủ × đơn giá tủ. Tổng trước thuế = tổng thành tiền các tủ, không cộng lại cả dòng chi tiết.
- Thuế suất là đầu vào được chọn/xác nhận; không coi giá trị mặc định là xác nhận thuế áp dụng thực tế.
- Không có tham chiếu vòng. Báo giá rỗng phải có tổng bằng 0 và trạng thái chưa đủ dữ liệu, không thể tự tham chiếu.
- Phân biệt giá catalog, giá ước tính và giá chưa có. Giá chưa có phải ghi “Chưa có giá”, không diễn giải số 0 thành miễn phí.
- Đề xuất tương đương phải giữ thông số nguồn để đối chiếu. Không cam kết chọn lọc bảo vệ hoặc tương thích 100% nếu chưa có tính toán/bằng chứng tương ứng.
- Nếu Excel hoặc CAD lỗi, trả trạng thái thiếu đầu ra cụ thể; không báo hoàn tất cả hai khi chỉ có một file.

## 6. Nghiệm thu

1. Lập bộ mẫu chuẩn do người kiểm tra chốt: ảnh rõ/mờ, PDF nhiều trang/nhiều tủ, DWG/DXF, bảng ký hiệu và tag trùng.
2. Đo riêng: phát hiện đúng/thiếu/thừa, đúng loại/thông số, sai lệch số lượng, đúng tủ và vùng ảnh chứa đúng ký hiệu. Không thay bằng tỷ lệ “có box”.
3. Với một hồ sơ định phát hành, đối soát toàn bộ thiết bị quan trọng và các dòng thiếu thông số/giá; không chấp nhận suy luận chưa được đánh dấu.
4. CAD và báo giá phải đồng nhất số lượng, phụ kiện và phân tủ; kiểm tra lại tổng sau khi đổi số lượng/giá/số tủ.
5. Chạy kiểm thử hồi quy, mở DXF và Excel trong phần mềm đích trước khi phát hành chính thức.

Lệnh kiểm thử offline từ thư mục BE_AIDE:

```powershell
.\venv\Scripts\python.exe -m unittest scripts.test_analysis_audit_regressions scripts.test_cad_layout_regressions -v
```

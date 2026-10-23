# Kiểm tra mặt CAD LS và CHINT — 21/10/2026

Đã quét hồ sơ trong các thư mục LS/Chint, hồ sơ ở thư mục tổng hợp có hãng LS/CHINT và các mục được gán hai hãng trong chỉ mục hiển thị.

## Xử lý hướng nhìn

- Xác định lại 6 mặt CHINT bằng hình học và chữ đọc từ DXF: 4 mặt bên NP2 (NO/NC, đầu tròn/đầu nhô), 1 mặt trước bộ cầu chì RT36-00 và 1 bảng mặt trước nhiều thiết bị NP2.
- Bảng NP2 được phân loại ASSEMBLY_REFERENCE, không coi là một nút nhấn hoặc một mã hàng. Sửa quy tắc áp dụng thông tin cũ để không đổi ngược bảng này thành PUSHBUTTON. Bằng chứng gán mặt được ràng buộc bằng SHA256 tệp nguồn.
- Gỡ 3 bảng tổng hợp chứa nhiều thiết bị/hãng/hướng nhìn khỏi thư viện và chỉ mục tải. Đã chuyển CadDon ra khỏi thư mục thư viện hoạt động; bản lưu phục hồi nằm trong removed-cad/. Nguồn TuLieuBanVe gốc được giữ để tra cứu, không công bố như một mặt thiết bị.
- Chỉ mục hiển thị LS/CHINT và dữ liệu khách hàng không còn hướng nhìn chưa xác định. Ba đường tải cũ trả 404.

## CAD bổ sung từ nguồn ngoài

- LS: 2 cụm đảo chiều AR-600 cho contactor 3P và 4P, mỗi cụm đủ 6 mặt (12 mặt). Mô hình gồm hai contactor, bộ liên động và đế gá; không liên kết giá phụ kiện AR-600 đơn lẻ cho toàn cụm.
- CHINT: NXM-250S 4P, đủ 6 mặt; kích thước mặt trước 140 × 165 mm khớp catalogue NXM trang PDF 27, đối chiếu mã tại trang 9; tham chiếu 4 dòng giá 180/200/225/250 A. Hai liên kết STEP có cùng SHA256 nên chỉ nhập một bộ hình học. Cần kiểm tra cơ cấu cực N và điện áp/Icu/Ics khi chọn mã.
- NXM 400/630 3P và một số STEP khác vẫn ở nguồn chờ vì cấu hình/chi tiết nhô chưa khớp bao hình danh nghĩa; không cắt bỏ tùy ý hoặc gán vào bảng giá.
- Tìm được 40 liên kết STEP NP2 trên cổng CHINT Hàn Quốc; tệp EA trả 404, cổng Trung Quốc trả 403. Chưa đưa các liên kết chưa tải/kiểm tra được thành CAD dùng được.

Nguồn: [CHINT NXM](https://www.chintglobal.com/global/en/products/low-voltage/iec/secondary-power-distribution/nxm.html), [CHINT NP2](https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/np2.html), [LS Metasol MS catalogue 202609, trang PDF 93](https://www.ls-electric.com/ko/cat/%5BMetasol_MS%5D_KO_C04001-37-202609.pdf).

## Kiểm tra

- 1.073 mặt hiện có được kiểm tra tồn tại, đọc/audit DXF và nhãn hướng; không có lỗi. Kiểm tra thêm các mặt có hãng được gán bởi chỉ mục hiển thị trong effective-brand-extra-audit.json.
- 21 tệp gốc có header inch đã được đối chiếu hợp đồng và SHA256 của bản ban_ve_mm.dxf; bản dùng để chèn là mm.
- 18 mặt mới đạt kiểm tra mm, audit, SHA256, bao hình, SVG, hình học không có chú thích; đủ 6 mặt của cùng biến thể. Đã kiểm tra bằng hình ảnh các mặt trước và chiều đặt.
- 48 lượt đọc dịch vụ DXF/SVG cho 18 mặt mới và 6 mặt đã sửa đạt; 3 đường tải bị gỡ trả 404; 41 bài kiểm tra đạt. API đã cập nhật và health 200.

## Phần còn thiếu

LS hiện có 336/517 dòng giá tham chiếu một bộ CAD họ đủ 6 mặt; 43 dòng có CAD thiếu mặt và 138 dòng chưa có CAD xác minh. Hai cụm LS mới không làm tăng độ phủ giá phụ kiện đơn. Không đánh dấu hoàn tất toàn bộ mã giá.

Chi tiết: [Danh sách cần bổ sung](cad-supplement-queue.json), [đối chiếu giá LS](pricebook-cad-coverage.csv), [kết quả công bố](publish-validation.json), [mặt đã xác định](resolved-views.json), [mặt đã gỡ](removed-views.json), [nguồn tìm bên ngoài](external-source-review.json).

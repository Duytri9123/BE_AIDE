# Cập nhật đối chiếu hình và danh mục thiết bị — 17/10/2026

Đã khôi phục bảng tên mã và thông số từ dữ liệu bảng giá/catalog gốc trong website và HTML ngoại tuyến. Giá là trường tùy chọn; thiếu giá không làm mất mã hàng. Giữ các cột, ô, thông số, tên hàng và mã đặt hàng gốc. Phân biệt mã trên CAD, mã dòng thương mại và mã đặt hàng; không đổi tên dòng A1 thành một mã đặt hàng tùy ý.

Đã đối chiếu 9.651 dòng nguồn. HTML ngoại tuyến hiển thị 22.560 lượt dòng thông tin cho 1.304 thiết bị; cùng dòng có thể được tham chiếu ở nhiều hồ sơ, đây không phải số SKU duy nhất. Trường hợp ABB A1 1P có 28 cấu hình A1 kèm mã đặt hàng, ngoài các lựa chọn tham khảo khác.

Phương pháp nhận diện gồm: chữ/thuộc tính/tên block từ DXF và DWG; OCR; so khớp ảnh nét CAD và tỷ lệ hình; tra ảnh sản phẩm/bản vẽ kích thước trên web; đối chiếu tài liệu hãng và các nguồn phân phối. Đã tính mô tả ảnh cho 2.073 lượt mặt, không lỗi; tìm được ứng viên hình tương tự cho 89 hồ sơ nguồn (88 thiết bị hiển thị sau gộp). Ứng viên được hiển thị với ảnh và tài liệu đối chiếu, không ghi thành hãng/model/thông số điện đã xác nhận. Không dùng điểm tương tự như xác suất nhận diện.

Nhật ký tìm ảnh từ nhiều nguồn ở catalog-visual-multisource-research.json. Các website khác nhau có thể đăng lại cùng một bản vẽ; số website không được coi là số chứng cứ độc lập. Những ứng viên mới chưa được tự xác nhận khi chỉ có một nguồn hoặc chỉ giống hình.

Đã kiểm thử việc giữ dòng không giá, giữ nguyên ô nguồn, phân biệt số cực, tên dòng và mã đặt hàng, ranh giới số trong mã, và vô hiệu hóa bằng chứng khi DXF/SVG thay đổi. Trình duyệt xác nhận bảng có 1SDA066485R1, ảnh CAD đối chiếu tải được, không có lỗi JavaScript. Build Vite thành công. Chưa coi toàn bộ các CAD chưa rõ mã là đã nhận diện xong.

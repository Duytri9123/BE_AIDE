# Thiết kế tủ điện và dữ liệu học từ thiết kế người dùng

Phiên bản 1.0, ngày 24/11/2026. Đối tượng sử dụng: người thiết kế tủ, người kiểm duyệt kỹ thuật và đội phát triển AI AIDE.

AIDE nên kết hợp quy tắc kỹ thuật có bằng chứng, tra cứu mẫu tương tự đã duyệt và học từ thay đổi trước–sau của người dùng. Số lượng thiết kế tăng chỉ giúp cải thiện khi nhãn đúng, phạm vi áp dụng rõ và kết quả được đo trên dự án độc lập. Lưu thêm thiết kế hoặc thêm tài liệu vào prompt chưa phải cơ chế học đã triển khai.

## Đọc theo nhu cầu

| Nhu cầu | Tài liệu |
| --- | --- |
| Hiểu cách thiết kế từ yêu cầu đến kiểm tra | [Quy trình và quy tắc thiết kế](01_QUY_TRINH_THIET_KE.md) |
| Biết phải thu thập gì cho từng cấu kiện | [Chi tiết và bằng chứng](02_CHI_TIET_VA_BANG_CHUNG.md) |
| Đánh giá hiện trạng và điểm cần sửa | [Đánh giá thiết kế và kiến trúc hiện tại](03_DANH_GIA_HIEN_TRANG.md) |
| Xây dựng cơ chế AI học từ phản hồi | [Đặc tả học và đánh giá độ chính xác](04_AI_HOC_TU_THIET_KE.md) |
| Dùng cơ chế đã tích hợp trong tab Thiết kế | [Triển khai bộ nhớ thiết kế](05_TRIEN_KHAI_CO_CHE_HOC.md) |
| Xem kết quả chạy thật và phạm vi đã kiểm tra | [Thiết kế E1 trong hệ thống](06_KET_QUA_CHAY_THAT_E1.md) |
| Tra từng mẫu vỏ và từng handle chi tiết gốc | [Danh mục 108 hồ sơ mẫu](DANH_MUC_MAU.md) |
| Nạp nguồn vào bộ lập chỉ mục hoặc công cụ AI | [Danh mục JSONL](source_inventory.jsonl) và [kết quả kiểm kê](audit_summary.json) |
| Định dạng một phản hồi dùng cho học | [JSON Schema](learning_event.schema.json) và [ví dụ minh họa](learning_event.example.json) |

## Ba loại nguồn mang tên form tủ

Cơ chế mới cho bố trí theo chức năng, phụ kiện đi kèm, chọn cỡ, khối mặc định và học bố trí dùng chung được mô tả trong [Thiết kế chức năng và mặc định](07_THIET_KE_CHUC_NANG_VA_MAC_DINH.md).

| Nguồn | Số bản ghi tại lần kiểm kê | Ý nghĩa và giới hạn |
| --- | ---: | --- |
| `BE_AIDE/data/CatalogTB/Form tủ/catalog.json` | 108 mẫu đang dùng, 2 mẫu loại trừ | Vỏ tủ dự án đã tách làm sạch; có tham chiếu bố trí và tuyến đồng gốc riêng |
| `D:/data/cabinet_templates/formtu/manifest.json` | 297 | Mẫu vỏ nguồn từ FOMTU, gồm 133 nhãn trong nhà, 97 ngoài trời, 67 chưa rõ; chưa đồng nhất với 108 mẫu dự án |
| `BE_AIDE/data/device_layouts/formtu/manifest.json` | 265 | Block chi tiết, không phải 265 vỏ tủ; đơn vị/model/hướng nhìn cần xác minh |

Danh mục máy đọc chứa 672 bản ghi gồm cả hai mẫu loại trừ. Các số trên là số bản ghi, chưa khử trùng hình học giữa ba thư viện. Mỗi ID có namespace riêng; không cộng chúng thành số mẫu thiết kế độc lập đã duyệt.

Form phân khoang 1, 2a, 2b, 3a, 3b, 4a, 4b là thuộc tính khác với mẫu vỏ. Hai lớp cánh không xác định Form 2. Đọc tiêu chí từng form trong `catalog.json` cùng hồ sơ `separation_review`; giữ `verified_form=null` khi chưa có bằng chứng về vách và khoang.

## Trạng thái dữ liệu học

Mọi bản ghi sinh trong gói này có `training_eligible=false`, `fabrication_approved=false`. Chúng dùng để truy xuất nguồn và lập hàng đợi xác minh. Để trở thành ví dụ thiết kế đúng, cần thêm yêu cầu dự án, hình học lắp thực, kiểm tra áp dụng và người duyệt theo đặc tả học. Ví dụ JSON là dữ liệu giả lập để minh họa hợp đồng, không thuộc bộ học.

108 hồ sơ liệt kê mặt, tệp bằng chứng, các block xuất hiện và handle. JSONL giữ thêm tọa độ, góc, tỷ lệ, tuyến hình học tham khảo và SHA256 tệp. Việc hiện diện của block hoặc tuyến màu chưa xác nhận model, số lượng vật lý hay vật liệu đồng. Hồ sơ chưa thay thế bản vẽ lắp đặt đúng model.

## Cập nhật danh mục

Chạy từ thư mục workspace:

```powershell
python -X utf8 BE_AIDE/scripts/build_cabinet_learning_docs.py
```

Có thể chỉ định `--legacy-formtu <thư mục nguồn>` và `--output <thư mục đầu ra>`. Script chỉ đọc dữ liệu nguồn và ghi tài liệu vào đầu ra; không import dịch vụ, đọc database hoặc sửa CAD/catalog. Khi thiếu manifest cũ, báo `legacy_manifest_available=false`; không hiểu số 0 là thư viện cũ đã được kiểm tra và rỗng. Hồ sơ sinh được ghi lại theo ID; khi catalog loại mẫu, dùng một thư mục đầu ra mới để tránh hồ sơ cũ còn lưu trên đĩa bị hiểu là mẫu đang hoạt động. Danh mục hiện hành luôn lấy theo `DANH_MUC_MAU.md` và JSONL mới nhất.

`audit_summary.json` xác nhận tồn tại và hash các tệp tham chiếu, không xác nhận hình học bằng cách mở CAD hoặc kiểm duyệt kỹ thuật. Ngày tài liệu dùng giờ Việt Nam; timestamp kiểm kê là UTC.

Kết quả kiểm tra gói tài liệu nằm trong [verification.json](verification.json): cú pháp Python/JSON, liên kết nội bộ, hash nguồn và hợp đồng JSON Schema. Kiểm tra schema chỉ xác nhận cấu trúc và một số điều kiện chặn; dịch vụ vẫn phải xác minh tính đầy đủ của bộ checks, quyền người duyệt, nội dung bằng chứng và quan hệ revision.

## Nguồn đọc chính

- [Quy tắc chọn form và bố trí hiện có](../QUY_TAC_CHON_FORM_VA_BO_TRI.md).
- [Trình tự thiết kế và khoảng cách](../TRINH_TU_THIET_KE_VA_KHOANG_CACH.md).
- [Quy tắc phân tích thiết bị](../QUY_TAC_PHAN_TICH_THIET_BI.md).
- [Giới hạn mô hình 3D và hợp đồng lắp đặt](../cabinet-solid-preview.md).
- [Triển khai thư viện và CAD tham khảo](../catalogtb-layout-deployment.md).
- [Hướng dẫn AI dùng thư viện CAD v2](<D:/data/thu_vien_tu_dien_v2/AI_CAD_LIBRARY_GUIDE.md>) và [quy tắc quản lý thư viện cũ](<D:/data/thu_vien_tu_dien_v2/README_library_curation.md>).
- [Quy tắc chọn và bố trí của bộ form nguồn](<D:/data/thu_vien_form_tu_cong_nghiep/03_quy_tac_chon_va_bo_tri.json>) và [bảy form nguồn](<D:/data/thu_vien_form_tu_cong_nghiep/02_bay_form_iec_61439.json>).
- [IEC 61439-2:2020, phạm vi và thông tin phiên bản](https://webstore.iec.ch/en/publication/30043). Trang IEC mô tả thay đổi về phân khoang và bảo vệ phần còn mang điện; tài liệu dự án phải chỉ rõ phiên bản tiêu chuẩn áp dụng.

Đặc tả mục 04 mô tả kiến trúc đầy đủ. [Mục 05](05_TRIEN_KHAI_CO_CHE_HOC.md) ghi phạm vi đã triển khai: lưu lịch sử, duyệt/thu hồi, học ưu tiên CAD và tái sử dụng bố trí có kiểm tra trong tab Thiết kế. Các hồ sơ kiểm kê ban đầu vẫn chưa có nhãn duyệt; việc tích hợp cơ chế không tự chứng nhận mẫu tủ.

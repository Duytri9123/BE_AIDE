# Cụm thiết bị, chiết khấu và thư viện hình LS

Triển khai ngày 23/09/2026.

## Cụm thiết bị

Mỗi cụm cần phân biệt thiết bị cha, thành phần có bằng chứng và thành phần còn cần đối chiếu. Ví dụ đồng hồ ampe + AS không được hiểu là đã đủ vật tư chỉ vì có một dòng tên cụm. Hệ thống hiển thị việc cần kiểm tra mã, số lượng và phạm vi bộ.

- Phụ kiện có bằng chứng và tag riêng được tách thành dòng độc lập, giữ tủ và nguồn. Không đặt tag CT/FU/PL giả bằng code.
- Phụ kiện có bằng chứng nhưng chưa có tag vẫn nằm dưới thiết bị cha; không bị bỏ và không tự đổi số lượng thành ba.
- Thành phần do AI nghi thiếu nhưng không có bằng chứng được giữ ở danh sách cần đối chiếu, chưa cộng vào BOM.
- Kiểm tra theo tủ: thông số đóng cắt còn thiếu, tham chiếu upstream chưa tìm thấy, cụm contactor chưa có bằng chứng bảo vệ quá tải liên kết, đồng hồ/chuyển mạch gộp, nguồn còn thiếu.
- Các kiểm tra trên là kiểm tra mức tối thiểu dựa trên dữ liệu; không bảo đảm phát hiện mọi thiếu sót. Không tự báo điểm an toàn, đạt IP/tiếp địa/chọn lọc bảo vệ từ tên thiết bị hoặc dòng tổng.
- Kết quả lịch sử khi đọc lại qua schema được bổ sung phần đánh giá mới nếu chưa có `cluster_review`. Không ghi đè BOM lịch sử trong DB.

Trong workspace, mở **Kiểm tra cụm thiết bị và tính đầy đủ** để xem các vấn đề và thành phần cụm.

## Chiết khấu hãng

Trong bảng báo giá có ô **Chiết khấu nhà sản xuất (%)** cho từng hãng ở các dòng thiết bị/phụ kiện. Nhập 0..100; giá niêm yết không bị ghi đè. Thiết lập được nhớ theo dự án trên trình duyệt và gửi khi Lưu file/Xuất Excel. Máy hoặc trình duyệt khác chưa tự đồng bộ thiết lập này.

Excel giữ J = giá niêm yết, K = chiết khấu %, G = J × (1 − K/100), H = số lượng × G. Công thức giữ cả khi chiết khấu ban đầu bằng 0 để sửa trực tiếp trong Excel. Ví dụ giá 1.000.000, chiết khấu 25%, số lượng 2 → 1.500.000 trước VAT. Chiết khấu chỉ áp dụng cho hãng khớp, không tự trừ vỏ tủ/nhân công có xuất xứ VN. Tổng tủ và VAT dựa trên giá đã giảm. Không trừ hai lần.

API `/export/excel` và `/export/save-to-project` nhận `manufacturer_discounts`, ví dụ `{"LS":25,"Schneider":15}`. Backend từ chối giá trị âm, trên 100 hoặc không hữu hạn. Chiết khấu này thuộc bảng báo giá; chưa ghi thành chính sách chiết khấu toàn hệ thống hoặc thay giá catalog.

## Thư viện LS

Nguồn được người dùng cung cấp: `C:/Users/admin/Desktop/cad/@LS_recover.dwg`. SHA-256 trùng bản `data/catalog_sources/ls_2026-10-01/LS-device-library.dwg`:

`F1AD44B1D5BB7B0042E58BFF3350E242A6070F1938F46B616431E2BA31574A20`

Dùng DXF đã xuất trong workspace (`../tmp/pdfs/ls_price/LS_recover.dxf`) và chỉ mục 150 block để tách hình. Không thay đổi DWG gốc, không gán nhãn chứng thực chính hãng chỉ dựa trên tên file.

- 149 block xuất thành file riêng trong `data/device_layouts/ls/`.
- `manifest.json` chứa tên block gốc, file nguồn, kích thước bao, đơn vị, hash và trạng thái chưa xác minh model/hướng nhìn.
- Mỗi file có một block reference ở modelspace; giữ các block phụ thuộc. Bounding box được dịch về góc dưới trái (0,0), đơn vị mm, không tự co kéo theo kích thước ước tính.
- `hgm1000-1250` bị loại khỏi manifest vì audit DXF yêu cầu sửa chữa.
- Bộ chuyển có cảnh báo không sao chép đầy đủ FIELD và metadata block động. Các file dùng làm hình bố trí tĩnh; chưa bảo đảm giữ hành vi dynamic block, thuộc tính hoặc field tự cập nhật.
- Không coi 149 block là 149 model khác nhau: thư viện có nhiều hướng nhìn, biến thể và khung thiết bị.
- Ví dụ `LS 800AF 3P` đã render kiểm tra hình. Chưa xác minh trực quan toàn bộ 149 file và chưa ghép tự động SKU→block.

Trong workspace mở **Thư viện hình thiết bị LS**, tìm tên, tải DXF rồi nhập vào công cụ CAD để copy/bố trí. Lượt này cung cấp thư viện tách sẵn và tải file; chưa có kéo thả trực tiếp block từ thư viện vào bản vẽ đang mở hoặc tự bố trí đúng model.

API thư viện yêu cầu đăng nhập: `GET /cad-library?q=...`, `GET /cad-library/{id}/dxf`. Chỉ tải ID có trong manifest; không nhận đường dẫn tùy ý.

## Kiểm chứng

Chạy từ BE_AIDE:

```powershell
.\venv\Scripts\python.exe -m unittest scripts.test_cluster_discount_library scripts.test_analysis_audit_regressions scripts.test_cad_layout_regressions -v
```

Frontend: `pnpm --filter @mlightcad/cad-viewer-example build` thành công. Lệnh type-check toàn workspace chưa đạt do lỗi tại cad-agent-plugin, cad-viewer và các dependency hiện có; không coi production build là bằng chứng type-check sạch. Chưa kiểm thử thao tác trình duyệt end-to-end hoặc gọi lại AI trên bộ bản vẽ chuẩn.

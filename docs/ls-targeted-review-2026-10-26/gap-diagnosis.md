# 170 dòng tồn đọng thực chất là gì?

170 là số dòng trong bảng giá chưa có bộ đủ sáu mặt cùng cấu hình, không phải số thiết bị không có bản vẽ. Các dòng này có 146 tên SKU: 127 tên ở nhóm chưa ghép được và 19 tên ở nhóm đã có CAD thiếu mặt. Tên SKU trùng vẫn có thể khác dải dòng, cuộn, tiếp điểm hoặc trang nguồn, nên không được gộp bằng tên đơn thuần.

| Nhóm bảng giá | Chưa ghép CAD được chứng minh | Đã có CAD nhưng thiếu mặt |
|---|---:|---:|
| ACCESSORY | 68 | 0 |
| MCCB | 18 | 4 |
| MCB | 32 | 0 |
| ELCB | 7 | 0 |
| RCBO | 2 | 0 |
| SPD | 13 | 2 |
| CONTACTOR | 3 | 11 |
| RELAY | 0 | 8 |
| METER | 2 | 0 |
| Tổng | 145 | 25 |

Category MCCB bao gồm 12 dòng phụ kiện, và CONTACTOR có MW-9bB~22bB là bộ dây. Cộng với 68 ACCESSORY, có ít nhất 81 dòng phụ kiện trong 170 dòng. Không nên mô tả cả 170 là thân máy cắt/contactor/relay không có CAD.

## Vì sao những dòng đã có CAD vẫn nằm trong danh sách?

Quy tắc hoàn tất hiện yêu cầu front/rear/left/right/top/bottom của cùng một biến thể. Nhãn chung “Mặt bên” không chứng minh được bên trái lẫn bên phải. Do đó một nguồn hai hoặc ba hình chiếu vẫn là gap, dù người dùng đã xem được CAD. Trong 25 dòng này, các vai trò đã xác định của bộ tốt nhất là: 12 dòng chỉ có front; 12 dòng front+rear; một dòng bottom+front. Các mặt bên chung vẫn là hình nguồn hợp lệ, chỉ không được tính thành hai hướng cụ thể.

Đây là quy tắc kiểm kê sáu mặt, không phải bằng chứng rằng tệp CAD hỏng. Không đổi quy tắc hoặc tự nhân đôi mặt để giảm số tồn đọng.

## Đã kiểm tra lỗi phần mềm nào?

- Các đợt trước đã sửa ưu tiên ID dòng giá được duyệt, bổ sung chỉ mục để khắc phục preview 404, và chặn ghép cùng series khác khung. Không thể khẳng định mọi tồn đọng trước đây chỉ do thiếu nguồn.
- Kiểm tra hiện tại đối chiếu 145 dòng chưa ghép với tất cả hồ sơ LS có `source_row_id`, không bị ẩn và được đánh dấu `source_row_scope=explicit_only`, `row_links_reviewed=true`: **không có hồ sơ đã duyệt như vậy bị API từ chối**. Đây là kiểm tra đường liên kết, không chứng minh ngoài kho hiện tại không tồn tại CAD phù hợp.
- Các liên kết chỉ là ứng viên hoặc thiếu bằng chứng cấu hình vẫn không được nâng thành liên kết đã duyệt.
- 60 hồi quy gần nhất đạt; HTTP lần triển khai gần nhất kiểm tra 25 dòng giá, 66 tệp CAD nguồn khớp hash, hai preview và ba mẫu visibility.

## Cách hiểu đúng phần chưa xử lý

145 dòng là “chưa có liên kết CAD được chứng minh trong dữ liệu hiện tại”, không phải “không có CAD trên thị trường”. 25 dòng là “có CAD nhưng chưa đạt sáu mặt”. Phần tiếp theo cần tập trung kiểm tra các nguồn ứng viên chưa nhập, xác minh biến thể, và tìm mặt còn thiếu. Năm cặp GMP lặp trang 4/8 là vấn đề chuẩn hóa trình bày riêng, không được tự xóa vì vẫn có ID nguồn riêng.

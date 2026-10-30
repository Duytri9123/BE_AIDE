# LS: chọn thiết bị và mặt CAD

Đã sửa cửa sổ chi tiết dòng giá để gọi API theo ID dòng, hiển thị thông tin và bộ CAD được liên kết rõ. Không dò bằng tên rồi lấy ảnh của mã khác. Tách từng cad_variant_id trong cùng hồ sơ; bộ mặt khác không trộn vào một menu.

Trong bản xem: bấm thiết bị để chọn, nút tam giác mở menu mặt của đúng bộ CAD. Chỉ viền chọn màu xanh; ảnh dùng màu gốc. Bản xem SVG tăng độ rõ nét ở kích thước màn hình bằng non-scaling-stroke, giữ tọa độ path và màu. Nét được giữ đầy đủ, không dùng hình bao thay chi tiết. Chưa tạo thêm màu nguồn bị mất trong các bản chuyển đổi trước đây.

DXF tải về mặc định giữ màu/layer/lineweight/đơn vị/tọa độ, gom đúng một mặt thành một block để chọn một lần. Không trộn mặt khác vào model space. Đây là block tĩnh; chưa tạo hoặc kiểm chứng dynamic visibility block DWG với menu ngay trong AutoCAD như ảnh người dùng. Không báo tính năng đó đã xong.

Kiểm tra: 45 unittest đạt; Vite production build đạt. Kiểm tra desktop/mobile với fixture của dữ liệu LS thật, chuyển 6 mặt và gọi đúng một ID dòng giá; chưa dùng phiên đăng nhập người dùng thật. Typecheck toàn monorepo còn lỗi có sẵn ở status bar icon, OrbitControls và rollup; Vite build vẫn thành công.

Giá công khai chỉ hiện giá chưa VAT có căn cứ: giữ nguyên giá nguồn khi nguồn chưa VAT; quy đổi chỉ khi tài liệu nêu rõ thuế suất. Giá nguồn chưa rõ thuế giữ nguyên nội bộ và tạm không hiện thành giá thuần. LS 517 dòng nguồn ghi chưa VAT; Morele nguồn 2021 ghi chưa VAT.

Rà LS: 517 dòng giá; 379 liên kết họ CAD, 138 còn thiếu; 336 có bộ sáu hướng, 43 liên kết chưa đủ hướng. Không có lỗi đường dẫn/nhãn trống trong lượt audit, nhưng không đồng nghĩa mọi SKU đã khớp hình học. Morele đã bổ sung danh mục giá có mã rõ, chưa tạo CAD thay hãng. Nguồn CAD CHINT/LS tiếp tục phải đối chiếu trước công bố.

FE commit 890df7d4 đã push origin/main. Trạng thái triển khai production chưa xác minh được từ GitHub API công khai (repo trả 404); không báo đã deploy. API thay từng worker, giữ Celery đang phân tích; /health trả 200.

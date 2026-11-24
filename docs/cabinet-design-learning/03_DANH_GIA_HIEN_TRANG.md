# Đánh giá dữ liệu và cách thiết kế hiện tại

## Kết luận đánh giá

Hệ thống đã có nền tảng tốt để thiết kế dựa trên CAD nguồn: tách vỏ sạch khỏi bố trí cũ, lưu handle, giữ nhiều mặt, hạn chế co giãn và phân biệt bản nháp với bản duyệt. Điểm còn thiếu để AI cải thiện có kiểm chứng là chuẩn hóa bằng chứng cho từng trường và lưu lịch sử phản hồi có nhãn theo phiên bản. Nên triển khai tra cứu mẫu đã duyệt trước, sau đó mới học xếp hạng hoặc tinh chỉnh mô hình khi dữ liệu đủ sạch.

Đánh giá này dựa trên metadata toàn bộ ba danh mục và đọc các module dưới đây. Chưa phải kiểm tra trực quan toàn bộ DWG/DXF hoặc chạy lại mọi pipeline. Kết quả kiểm tra cũ trong tài liệu được xem là lịch sử; số kiểm kê mới lấy từ [audit_summary.json](audit_summary.json).

## Kiểm tra dữ liệu vỏ tủ và formtu

| Chỉ tiêu kiểm kê | Kết quả | Ý nghĩa đối với thiết kế và học |
| --- | ---: | --- |
| Mẫu vỏ dự án hoạt động | 108 | Có thể tạo hồ sơ truy xuất từng mẫu |
| Mẫu loại trừ | 2 | Giữ lý do loại trừ; không đưa vào tập thiết kế đúng |
| Mẫu có profile resize | 96/108 | Có metadata biến đổi; cần kiểm tra đúng kích thước danh nghĩa và giới hạn khi sử dụng |
| Mẫu cho phép `auto_select=true` | 0/108 | Không đổi cờ chỉ vì đã lập hồ sơ |
| Mẫu có `verified_form` khác null | 0/108 | Chưa có nhãn form xác minh để huấn luyện bộ chọn form |
| Mẫu còn block chưa định danh theo metadata | 105/108 | Tên block và giữ nét cơ khí chưa đủ xác nhận ý nghĩa |
| Mẫu nguồn FOMTU cũ | 297 | Chưa chứng minh độc lập với thư viện mới hoặc phù hợp chế tạo |
| Block thư viện formtu | 265 | Là chi tiết; không phải bộ thiết kế tủ hoàn chỉnh |
| Block có `model_verified=true` | 0/265 | Chưa dùng nhãn tên block làm model thật |
| Block thiếu width_mm hoặc height_mm | 265/265 | Chưa đủ nền tảng kích thước mm cho học bố trí |
| Đơn vị ghi trên block | 265 nhãn inch | Cần đối chiếu DIM và tỷ lệ thực; không tự chuyển hàng loạt |
| Tệp tham chiếu thiếu trong phạm vi kiểm kê | 0 | Kiểm tra tồn tại/hash đạt; chưa kiểm tra đúng nội dung và hình học |

Các số không phải tỷ lệ thiết kế đúng/sai. 105 mẫu còn block chưa định danh không có nghĩa 105 mẫu bị sai cơ khí. Ngược lại, không có tệp thiếu cũng chưa xác nhận nguồn hợp lệ.

Tài liệu thư viện v2 cũ có các mốc 339 khung nguồn, 727 nhóm CAD hoặc 715 nhóm trong những bản hướng dẫn khác nhau. Đó là các phạm vi/phiên bản kiểm kê cũ; không dùng chúng thay 297 bản ghi manifest formtu hiện tại hoặc 108 mẫu hoạt động. Khi hợp nhất nguồn phải lưu ngày, manifest hash, trạng thái loại trừ và nhóm khử trùng. Quy tắc cập nhật đúng của hướng dẫn cũ vẫn hữu ích: xác minh từng thuộc tính và biến thể, không đánh dấu cả thiết bị đạt chỉ vì đã nhận ra hãng.

## Kiểm tra luồng chọn form và bố trí

| Khâu | Điểm đã có và bằng chứng mã nguồn | Rủi ro hoặc giới hạn | Hướng xử lý |
| --- | --- | --- | --- |
| Lấy mẫu vỏ | `cabinet_templates.inventory`, `resolve`, `source_path` | Trạng thái danh mục là `needs_review`; không phải kho mẫu đạt | Giữ eligibility riêng cho truy xuất, layout và chế tạo |
| Xếp hạng kích thước | `cabinet_templates.candidates` lọc loại và tính khoảng cách log kích thước | Gần kích thước chưa chứng minh đủ vùng lắp, cáp hoặc nhiệt | Dùng khoảng cách làm thứ tự thử; kết quả khả thi phải do kiểm tra bố trí |
| Đổi kích thước | `resize_profile` đối chiếu nominal; `candidates` kiểm tra chiều hỗ trợ và 75–125%; `stretch_axes` dùng DIM | Có profile không đồng nghĩa mọi kích thước mới phù hợp cơ khí | Kiểm tra anchors, mặt, phần cứng, quỹ đạo và kết cấu sau đổi |
| Chọn mặt lắp | `device_installation`, `PhysicalLayoutEngine.classify_mounting` tách thân trong với panel | Các nhánh suy đoán bằng tên/loại vẫn cần kiểm tra đúng model | Đưa bằng chứng mặt dự án/model lên trước; chặn trường chưa xác định |
| Lỗ khoét | `_validated_cutout` kiểm model, biến thể, polygon và hash | Front bbox không cung cấp lỗ khoét; thiếu contract thì không có lỗ tự động | Bổ sung bản vẽ lắp và hợp đồng đúng model, không dựng hình chữ nhật thay thế |
| Bản nháp | `ReferenceLayoutGenerator.generate` có nhãn và `release_ready=false` | Fallback có khoảng chừa cố định và suy mặt cho một số nhóm | Giữ hoàn toàn trong luồng review, không dùng làm nhãn đạt |
| Bố trí 3D | `cabinet_preview_3d`, `cabinet_topology`; tài liệu preview nêu rõ giới hạn | Độ sâu phụ kiện và nhiều phần hình học là tham khảo | Gắn chứng cứ từng chi tiết; kiểm cơ khí riêng trước phát hành |
| Khoảng cách theo dòng | `design_policy.dimensions_for_current`, `fishbone_rstn.json` | Quy tắc dự án có thể bị hiểu nhầm thành chuẩn điện | Lưu `rule_type=user_policy`, phạm vi và phần còn thiếu |

Đường dẫn mã được giải quyết từ `BE_AIDE/app/services/cad/`. Các nhận xét trên mô tả logic đọc được, không chứng minh mọi nhánh luôn được gọi trong mọi phiên thiết kế.

### Mâu thuẫn cần chuẩn hóa trong tiêu chí form

`separation_review.required_checks` và `phan_tich_bo_tri_va_form.json` có các giá trị boolean như `terminals_from_busbars=false` cho 2a/3a. Cách này dễ trộn “không bắt buộc tách” với “bắt buộc không tách”. Đề xuất lưu quy tắc bằng `require`, `optional` và điều kiện quan hệ khoang; lưu quan sát bằng `true`, `false`, `unknown` riêng. Việc một mẫu thỏa thêm điều kiện phải được giải thích theo phạm vi yêu cầu, không tự coi là lỗi hoặc tự chứng nhận form cao hơn.

Đây là đề xuất sửa biểu diễn; tài liệu này không thay catalog. Kiểm chứng lại bảng phân khoang bằng tài liệu tiêu chuẩn áp dụng trước khi viết validator.

Căn cứ cho cách diễn đạt “không bắt buộc tách” là [ABB workbook, bảng trang in 51](https://library.e.abb.com/public/32f98df19e5849e1b6b5d6172e00be73/2CPC000313B0201.pdf). Khi nghiệm thu theo phiên bản cụ thể, dùng bộ tiêu chí đã được người phụ trách kỹ thuật chốt cho phiên bản đó.

### Mâu thuẫn cần chuẩn hóa trong chính sách mặt và bản nháp

`fishbone_rstn.json` còn `default_operator_devices_face=outer_door`, trong khi các module lắp đặt và quy tắc mới yêu cầu xác định mặt theo dự án/model. `reference_layout.py` fallback cũng còn suy cánh ngoài cho LIGHT/METER/SELECTOR và dùng khoảng chừa cố định. Nên hợp nhất quy tắc mặt và provenance để phương án tham khảo không bị nạp vào kho đã duyệt. Không dùng sửa đổi sở thích để hợp thức hóa thân MCCB trên cánh.

## Kiểm tra lưu thiết kế và khả năng học

`app/api/v1/endpoints/projects.py` có GET/PUT `/{project_id}/cabinet-designs`, kiểm quyền dự án và lưu tại `storage/cabinet-designs/{id}.json`. `project_design_store.save_designs` dùng khóa liên tiến trình, revision chống ghi đè và replace file nguyên tử. Đây là nền tảng lưu bản hiện tại có bảo vệ xung đột.

Hàm lưu ghi đè snapshot `designs` cùng revision mới, không giữ journal thay đổi hoặc lịch sử revision trong module này. Các route kiểm hình thức danh sách/id/name, chưa phải hợp đồng nhãn học theo từng trường. Việc có feedback giữa các vòng đọc sơ đồ ở các module AI không chứng minh đã có học lâu dài từ thiết kế người dùng.

Trong các module đã khảo sát chưa thấy một luồng hoàn chỉnh nối sửa thiết kế → duyệt nhãn → tập dữ liệu có phiên bản → đánh giá độc lập → phát hành/rollback. Không suy kết luận đó thành tuyên bố mọi thành phần học đều vắng mặt trong toàn hệ thống.

## Tiêu chí đánh giá một thiết kế

Mỗi tiêu chí có kết quả `pass`, `fail`, `unknown`, `not_applicable`. Điểm số chỉ dùng so sánh các phương án đã qua các cổng bắt buộc. Gợi ý trọng số phục vụ UI: đầy đủ BOM 20%, phù hợp CAD/model 15%, cơ khí 20%, đấu nối 20%, điện và nhiệt 15%, bảo trì 10%. Đây là trọng số đề xuất, chưa hiệu chuẩn bằng dữ liệu.

Một thiếu sót nghiêm trọng như chưa biết khoảng cách điện, mất thiết bị, cấn cánh hoặc thiếu lỗ gá không được bù bằng các điểm khác. Nếu có kiểm tra bắt buộc fail/unknown thì vẫn chặn phát hành dù tổng điểm cao. Đối với thiết kế chỉ rà soát bố trí, phải ghi rõ phạm vi duyệt; không lấy nhãn đó xác nhận điện/nhiệt.

## Ưu tiên thực hiện

1. **Chuẩn hóa dữ liệu nguồn.** Xác minh đơn vị, mặt, model và chi tiết chưa định danh; khử trùng theo hình học/nguồn. Chọn một nhóm tủ và nhóm thiết bị có đủ bằng chứng để làm bộ mẫu chuẩn đầu tiên.
2. **Giữ lịch sử thiết kế.** Tách snapshot hiện tại và event bất biến, lưu before/after, lý do, actor, checks và revision; thêm nhãn phạm vi duyệt.
3. **Tra cứu có kiểm soát.** Chỉ lấy mẫu đã duyệt phù hợp yêu cầu và quyền dữ liệu; trả bằng chứng cạnh từng đề xuất, chạy lại toàn bộ kiểm tra.
4. **Đánh giá cải tiến.** Khóa bộ kiểm tra theo nhóm dự án/nguồn; so sánh cùng dữ liệu đầu vào và báo cả lỗi nghiêm trọng, tỷ lệ phải từ chối và thời gian sửa.
5. **Học xếp hạng sau khi đạt chất lượng nhãn.** Chỉ phát hành phiên bản cải thiện có ý nghĩa, có rollback. Fine-tuning là bước tùy kết quả thực nghiệm, không là điều kiện để bắt đầu tái dùng tri thức.

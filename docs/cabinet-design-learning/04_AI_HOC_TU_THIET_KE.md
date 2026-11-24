# Đặc tả AI học từ thiết kế đã được kiểm tra

Trạng thái ngày 24/11/2026: bộ nhớ lựa chọn CAD, lịch sử, duyệt/thu hồi và đề xuất bố trí đã triển khai trong [tab Thiết kế](05_TRIEN_KHAI_CO_CHE_HOC.md). Các mục huấn luyện mô hình và đánh giá độc lập dưới đây tiếp tục là kiến trúc mục tiêu.

## Mục tiêu và giới hạn

Mục tiêu là giảm sai sót và công sửa của người dùng trong những nhóm thiết kế có dữ liệu phù hợp. Cần đo riêng độ đúng nhận diện, khớp CAD/model, đủ BOM, bố trí khả thi và mức chấp nhận phương án. Không gộp thành lời hứa một tỷ lệ chính xác duy nhất cho mọi loại tủ.

Thiết kế nhiều hơn tạo thêm cơ hội học; chất lượng chỉ tăng khi phản hồi đúng và được đánh giá độc lập. Mẫu mới có thể làm mô hình kém đi nếu lặp cùng dự án, dùng đơn vị sai, chứa lỗi đã được người dùng bỏ qua hoặc khác ngữ cảnh. Cơ chế dưới đây là đặc tả cần triển khai; JSONL nguồn mới tạo chưa phải dữ liệu huấn luyện có nhãn.

## Kiến trúc đề xuất

```text
Yêu cầu + BOM + thư viện có phiên bản
                  |
      Lọc quyền và ràng buộc áp dụng
                  |
      Tra cứu mẫu đã duyệt phù hợp
                  |
      AI tạo các phương án có nguồn
                  |
      Kiểm tra hình học và kỹ thuật
                  |
      Người dùng sửa và ghi lý do
                  |
       Người có thẩm quyền duyệt
                  |
       Journal + kho tri thức chuẩn
                  |
   Lập chỉ mục / học xếp hạng ngoại tuyến
                  |
   Đánh giá tập giữ riêng → phát hành / giữ bản cũ
```

Bộ kiểm tra kỹ thuật chạy sau mỗi đề xuất, kể cả mẫu giống hệt từng được duyệt, vì BOM, phụ kiện, cáp hoặc catalog có thể đã đổi. Mô hình học chỉ gợi ý hoặc xếp hạng; không tự sửa bằng chứng nguồn hoặc cấp quyền phát hành chế tạo.

## Ba mức cải thiện

| Mức | Cách hoạt động | Dữ liệu đủ điều kiện |
| --- | --- | --- |
| Tra cứu mẫu tương tự | Lấy hồ sơ đã duyệt, trích lý do và cấu hình có nguồn đưa vào ngữ cảnh | Mẫu phù hợp phạm vi duyệt, còn hiệu lực và có quyền truy cập |
| Học sở thích và xếp hạng | Học người dùng chọn phương án nào giữa các phương án khả thi | Lựa chọn có ngữ cảnh và lý do; không diễn giải mọi thao tác kéo là sửa lỗi |
| Huấn luyện hoặc tinh chỉnh | Học tác vụ có nhãn rõ như chọn CAD, phân vai trò hoặc đề xuất bố trí | Tập đủ đa dạng, đã tách nguồn trùng và qua đánh giá chất lượng |

Khởi đầu với tra cứu và bộ quy tắc. Chọn mô hình huấn luyện dựa vào lỗi quan sát được; không đưa toàn bộ file CAD thô vào fine-tuning rồi kỳ vọng tự học mọi quan hệ cơ khí.

## Hợp đồng dữ liệu

| Thực thể đề xuất | Nội dung chính | Liên kết |
| --- | --- | --- |
| `source_artifact` | URI nội bộ, hash, revision, quyền, loại và hiệu lực | Làm căn cứ cho từng trường |
| `design_revision` | Yêu cầu, BOM, vỏ, chi tiết, tuyến, checks và model/catalog/policy version | Bản bất biến theo revision |
| `design_event` | Actor, timestamp, base/result revision, thay đổi trước–sau và reason | Phát sinh từ thao tác đã lưu thành công |
| `review_decision` | Người duyệt, vai trò, phạm vi, evidence, quyết định và lý do | Chốt nhãn và loại trừ |
| `knowledge_case` | Ngữ cảnh, phương án đúng trong phạm vi, trường đã xác minh, hạn chế | Đơn vị tra cứu |
| `dataset_version` | Danh sách case/event, split, nhóm trùng, license/permission và hash | Đầu vào bất biến cho đánh giá/học |
| `evaluation_run` | Baseline/candidate, test IDs, metric, lỗi, độ bất định | Điều kiện phát hành |
| `model_release` | Model/index/policy versions, kết quả so sánh, phạm vi và rollback | Phiên bản phục vụ |

Tái dùng endpoint cabinet-designs để lưu snapshot hiện tại; thêm journal và revision bất biến vào cùng giao dịch logic. Dùng transactional outbox nếu metadata và file nằm ở hai nơi: lưu pending event, lưu snapshot cùng revision, xác nhận committed rồi phát cho bộ học. Chống ghi trùng bằng event ID và idempotency key; sự kiện lỗi hoặc save bị 409 không được vào tập học.

Ví dụ hợp đồng ở [learning_event.schema.json](learning_event.schema.json). Schema kiểm hình dạng dữ liệu; các điều kiện về quyền, hash thực, liên kết revision và kỹ thuật phải do dịch vụ kiểm tra. Ví dụ đi kèm cố ý `is_synthetic=true`, `training_eligible=false`.

## Phân loại thao tác và nhãn

| Tình huống | Nhãn | Xử lý học |
| --- | --- | --- |
| Sửa nhận diện sai có nguồn đối chiếu | `correctness_fix` | Cặp trước–sau cho tác vụ đúng phạm vi sau khi duyệt |
| Dịch thiết bị để xử lý cấn cánh | `constraint_fix` | Học ràng buộc theo mặt, model và hình học cụ thể |
| Đổi cách căn hàng do thẩm mỹ | `preference_change` | Chỉ cá nhân hóa hoặc xếp hạng, không thành chuẩn kỹ thuật |
| Đổi BOM do khách hàng thay yêu cầu | `requirement_change` | Tạo ngữ cảnh mới; không gán phương án cũ là lỗi AI |
| Thử kéo rồi undo hoặc chưa lưu | `exploration` | Không dùng làm nhãn đúng |
| Phát hiện lỗi khi chế tạo | `fabrication_feedback` | Gắn revision thực tế, lỗi và sửa hoàn công; thu hồi nhãn cũ bị ảnh hưởng |
| Không có ý kiến hoặc chỉ nhấn lưu | Không có nhãn kỹ thuật | Giữ snapshot, không tự gán approved |

Nhãn “bố trí đã duyệt” và “đã chế tạo đạt” có phạm vi khác nhau. Một mẫu có thể đủ để học căn hàng nhưng chưa đủ để học khoảng cách điện. Vì vậy eligibility phải theo `task` và `verified_fields`, không chỉ một cờ approved cho cả tủ.

## Điều kiện đưa vào kho học

1. Sự kiện đã commit; base/result revision tồn tại, trước–sau đúng và actor có quyền.
2. Có yêu cầu áp dụng, provenance, đơn vị và ID chi tiết ổn định; không ghép bằng tag trần.
3. Người duyệt khác vai trò suy luận tự động, có thẩm quyền cho trường và phạm vi duyệt. Với sở thích, người dùng sở hữu lựa chọn có thể xác nhận trong phạm vi cá nhân.
4. Các kiểm tra liên quan tác vụ đạt. Fail/unknown loại khỏi nhãn thiết kế đúng; có thể giữ làm ví dụ lỗi nếu gắn rõ loại nhãn và target.
5. Không thuộc dữ liệu giả lập, bản nháp chưa duyệt, nguồn thu hồi hoặc nguồn không cho phép dùng học.
6. Đã xác định nhóm trùng theo dự án, CAD gốc, hình học, mẫu vỏ và dòng biến thể; chưa gán vào tập test đang khóa.

Đối với JSONL kiểm kê hiện tại, tất cả eligibility bằng false vì chỉ có dữ liệu nguồn, chưa có các quyết định duyệt theo hợp đồng trên. Không cần xóa nguồn chưa xác minh; giữ trong kho tham khảo với lý do chặn.

## Tra cứu và xếp hạng phương án

Lọc cứng theo quyền truy cập, môi trường, kiểu lắp, yêu cầu form, thiết bị đã chốt, hướng cáp, mặt lắp và khả năng dùng hình học. Trường bắt buộc chưa biết trả `needs_evidence`; không cho điểm giống cao vượt qua điều kiện thiếu.

Sau lọc, tính mức tương tự từ cấu trúc mạch/BOM, model/cực, form/khoang, hướng tuyến, tỷ lệ kích thước và kiểu thao tác. Có thể dùng vector để tìm ứng viên nhưng phải đối chiếu trường có cấu trúc trước khi dùng. Khử trùng ứng viên cùng nguồn để không tạo ảo giác nhiều bằng chứng độc lập.

Đề xuất khởi điểm cho reranker: cấu trúc/chức năng 30%, model và lắp đặt 25%, cấu hình vỏ/khoang 20%, tuyến cáp 15%, kích thước 10%. Đây là trọng số thử nghiệm cần đo; không phải xác suất đúng. Thông báo truy xuất phải nêu mẫu nào, giống ở đâu, khác ở đâu và dữ liệu nào còn cần xác minh.

Ví dụ cùng vỏ H700 W500 D250 nhưng một mẫu có nguồn vào trên, mẫu kia vào dưới: có thể dùng để tham khảo kết cấu, không chép nguyên bố trí. Một kết quả được duyệt với BKN không trở thành bằng chứng kích thước cho LA63 chỉ vì cùng hãng và cùng số cực.

## Cá nhân hóa và quyền dữ liệu

Kho cá nhân mặc định chỉ phục vụ chủ thể có quyền. Sở thích một người không tự trở thành quy tắc toàn hệ thống. Muốn dùng dữ liệu giữa người dùng/tổ chức phải có phạm vi cho phép rõ, khử thông tin khách hàng và kiểm duyệt đưa vào kho chung. Lọc tenant/ACL trước truy xuất nội dung; không chỉ ẩn tên khi đã đưa dữ liệu vào prompt.

Tách giá, tên khách hàng, địa chỉ, tài khoản và ghi chú nhạy cảm khỏi case kỹ thuật. JSONL sinh mới chỉ chọn trường kỹ thuật của manifest cũ, không sao chép bảng attributes chứa tên khách hàng. Nguồn CAD vẫn có thể chứa dữ liệu riêng: không gửi toàn tệp sang dịch vụ học khi chưa kiểm tra quyền và nội dung.

Khi người dùng xóa hoặc thu hồi quyền học, loại khỏi index, dataset tương lai và bộ cá nhân hóa; lưu dependency để biết release nào đã sử dụng nguồn. Nếu đã huấn luyện model, áp dụng chính sách tái huấn luyện/loại release phù hợp, không hứa xóa ảnh hưởng chỉ bằng xóa file. Log sự kiện thu hồi bằng ID nội bộ, giới hạn dữ liệu nhận dạng.

## Đo độ chính xác và công sửa

| Chỉ tiêu | Cách đo | Ý nghĩa |
| --- | --- | --- |
| Phát hiện thiết bị | Precision, recall, F1 theo thân vật lý, loại và tủ | Tách bỏ sót và nhận thừa |
| Khớp CAD | Tỷ lệ đúng model/biến thể/cực/hướng trong các dòng có nhãn | Không gộp CAD cùng họ thành exact match |
| BOM | Số lượng đúng theo từng tủ/tag/nhóm vật lý; thiếu/thừa riêng | Tổng bằng nhau chưa đủ |
| Chọn vỏ | Tỷ lệ vỏ vượt qua toàn bộ kiểm tra bố trí áp dụng | So với tập phương án hợp lệ, không chỉ một mẫu người dùng chọn |
| Hình học | Số va chạm, vượt biên, sai mặt và kiểm tra chưa biết | Báo cả fail và unknown |
| Công sửa | Trung vị thời gian và số sửa có ý nghĩa tới duyệt | Tách sửa do AI sai khỏi đổi yêu cầu |
| Chấp nhận lần đầu | Số phương án được duyệt không sửa kỹ thuật / số phương án đưa ra | Đi kèm độ bao phủ và mức khó |
| Độ bao phủ | Tỷ lệ hồ sơ có đủ bằng chứng để đề xuất | Chặn nhiều hơn có thể tăng độ đúng nhưng giảm hỗ trợ |
| Lỗi phát hành | Số lỗi nghiêm trọng lọt qua / hồ sơ phát hành được kiểm | Chỉ số chặn release, không bù bằng tốc độ |
| Độ tin cậy điểm | Đối chiếu confidence với tỷ lệ đúng thực tế theo nhóm | Confidence do AI tự báo không là accuracy |

Thiết lập baseline trước khi nạp case mới. Chia tập theo nhóm dự án và tổ tiên nguồn CAD; các revision, bản sao đổi kích thước và hình học gần trùng cùng nhóm phải ở cùng split. Tỷ lệ 70/15/15 chỉ là khởi điểm theo nhóm khi đủ dữ liệu; dữ liệu ít dùng kiểm tra chéo theo nhóm và một tập test khóa riêng. Giữ thêm tập mới theo thời gian để đo thay đổi nhu cầu.

Tập kiểm tra phải chứa tủ trong/ngoài nhà, một/hai lớp cánh, mẫu có bệ/mái, nhiều khoang, thiếu mặt, nhãn model gần giống, tag lặp, nguồn inch mâu thuẫn mm, thiết bị explode, thiếu dữ liệu cáp và trường hợp phải từ chối. Số case tối thiểu quyết định theo độ đa dạng và độ bất định của kết quả; không tự đặt 100 thiết kế là đủ cho mọi tác vụ.

## Điều kiện phát hành phiên bản cải tiến

So baseline và candidate trên cùng test set và cùng phiên bản catalog/policy, hoặc công bố rõ phép đánh giá thứ hai khi nguồn thay đổi. Báo số mẫu và khoảng tin cậy theo nhóm dự án, dùng so sánh cặp trên cùng case. Không kết luận cải thiện chỉ vì điểm trung bình cao hơn rất nhỏ hoặc do bỏ các case khó.

Release phải không có lỗi mới nghiêm trọng trong tập kiểm; chỉ tiêu chính cải thiện đủ mức có ý nghĩa do nhóm sản phẩm/kỹ thuật đặt trước; các nhóm tủ quan trọng không suy giảm quá ngưỡng đã thống nhất. Đây là điều kiện nghiệm thu cần chốt trước thí nghiệm, chưa có kết quả accuracy trong gói này.

Triển khai theo chế độ chạy song song đánh giá rồi mở dần theo phạm vi. Lưu đồng thời phiên bản model, index, policy, catalog và dataset. Khi lỗi tăng hoặc nguồn bị thu hồi, quay về bộ phiên bản trước; tiếp tục giữ journal để tái hiện lỗi.

## Tích hợp vào giao diện thiết kế

Người dùng vẫn thiết kế, kéo thả và lưu như hiện tại. Sau một sửa đổi đã lưu, có thể chọn lý do ngắn: sửa sai kỹ thuật, đổi yêu cầu, đổi bố trí theo sở thích, hoặc phản hồi xưởng. Hệ thống chỉ hỏi thêm trường ảnh hưởng nhãn; không buộc người dùng viết báo cáo cho mỗi thao tác.

Khi duyệt, hiển thị phạm vi “duyệt bố trí” và các kiểm tra còn thiếu; người duyệt xác nhận đúng quyền của mình. Mỗi đề xuất AI có lý do và nút mở bằng chứng. Việc người dùng tiếp tục làm việc hoặc tải bản nháp không tự trở thành chấp nhận kỹ thuật.

Các endpoint bổ sung như ghi event, duyệt revision, tìm case và chạy evaluation là API đề xuất; chưa được tạo trong thay đổi tài liệu này. Ưu tiên triển khai journal và bộ kiểm tra eligibility trước khi thêm job huấn luyện nền.

## Kịch bản nghiệm thu cơ chế học

| Kịch bản | Kết quả phải đạt |
| --- | --- |
| Hai cửa sổ sửa cùng revision | Một lần lưu thành công; lần xung đột không tạo event học |
| Gửi lại cùng event | Một sự kiện duy nhất, không tăng trọng số mẫu |
| Kéo thử rồi undo | Không tạo nhãn đúng từ vị trí đã bỏ |
| Đổi yêu cầu khách hàng | Revision mới giữ yêu cầu cũ; không ghi lỗi AI cho phương án cũ |
| Sửa cấn cánh có đủ nguồn và duyệt | Case được truy xuất cho ngữ cảnh tương ứng, vẫn kiểm lại |
| Một kiểm tra bắt buộc unknown | Chặn nhãn đạt trong phạm vi đó; giữ mẫu tham khảo |
| Block inch chưa rõ kích thước thật | Không chọn kích thước mm ngầm; trả mục cần xác minh |
| CAD/cutout đổi hash | Thu hồi trạng thái xác minh phụ thuộc, yêu cầu review lại |
| Một bản sao lọt train và test | Bộ kiểm tra dataset phát hiện và chặn evaluation |
| Người dùng A tra dữ liệu B không được chia sẻ | Không truy xuất nội dung hoặc lộ tên/tệp nguồn |
| Thu hồi case đã dùng | Loại khỏi index và truy được release phụ thuộc |
| Candidate kém baseline | Giữ release cũ; lưu báo cáo lỗi cho vòng tiếp theo |

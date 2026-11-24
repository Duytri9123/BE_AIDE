# Cơ chế học đã tích hợp vào tab Thiết kế

Ngày 24/11/2026. Phiên bản đầu triển khai bộ nhớ cá nhân từ lựa chọn CAD và bố trí do người dùng duyệt. Bộ nhớ tác động đến thứ tự tìm CAD cho thiết bị bóc tách và cho phép áp dụng bố trí tương thích. Chưa huấn luyện lại trọng số mô hình ngôn ngữ; tỷ lệ chính xác chỉ được công bố sau khi có bộ kiểm tra độc lập.

## Cách sử dụng

1. Mở dự án, chọn kết quả bóc tách và chuyển thiết bị sang **Tủ thiết kế**.
2. Hệ thống lọc CAD theo loại, hãng, model nguồn nếu có, số cực và các mặt nguồn có đơn vị mm. Nếu có lựa chọn đã duyệt cùng yêu cầu, ưu tiên lựa chọn đó. CAD họ thiết bị vẫn cần đối chiếu định mức điện theo biến thể.
3. Thiết kế, sửa bố trí và lưu. Mỗi lần lưu thay đổi có revision bất biến và nhật ký trước–sau.
4. Mở **AI học từ thiết kế**, chọn phạm vi, ghi phần đã đối chiếu rồi bấm **Duyệt để AI học**. Lưu bình thường không tạo nhãn duyệt.
5. Với thiết kế mới cùng vỏ, kích thước, yêu cầu và bộ CAD, bấm **Áp dụng bố trí đã học**. View kiểm lại mặt lắp, cơ cấu gá, bao hình và va chạm. Nếu không vượt qua kiểm tra, khôi phục phương án trước.
6. Bấm **Thu hồi** để loại mẫu khỏi các lần đề xuất tiếp theo. Thay đổi thiết kế hoặc hình học nguồn làm mẫu cũ mất hiệu lực cho đến khi duyệt lại.

Với phạm vi chọn CAD, có thể chỉ chọn các thiết bị đã kiểm tra để duyệt riêng; không chọn riêng thì hệ thống kiểm tra toàn bộ tủ. Duyệt bố trí luôn yêu cầu kiểm tra toàn bộ thiết bị.

Không bấm duyệt hộ người dùng trong ví dụ chạy thật. Các kiểm thử tạo nhãn duyệt chỉ chạy trong thư mục tạm.

## Các API được triển khai

Các đường dẫn dưới tiền tố `/api/v1/projects/{project_id}` đều kiểm quyền dự án qua tài khoản đang đăng nhập.

| API | Chức năng |
| --- | --- |
| `GET /cabinet-designs` | Đọc snapshot có revision từ kho giao dịch; tương thích JSON cũ |
| `PUT /cabinet-designs` | Lưu snapshot và nhật ký trước–sau trong một giao dịch |
| `GET /design-learning` | Lịch sử lưu, các lần duyệt, trạng thái hiệu lực và phiên bản bộ nhớ |
| `POST /design-learning/approve` | Duyệt revision và tủ đã lưu với phạm vi `device_selection` hoặc `layout` |
| `POST /design-learning/match-devices` | Tra CAD và ưu tiên lựa chọn đã duyệt có yêu cầu tương ứng |
| `POST /design-learning/layout-suggestion` | Tìm bố trí đã duyệt cùng ngữ cảnh từ tủ khác |
| `POST /design-learning/reviews/{review_id}/revoke` | Thu hồi mẫu, có thể gọi lại an toàn |

Phản hồi matching giữ `electrical_verification_required=true`. Endpoint không chốt mã đặt hàng hoặc chứng nhận điện/nhiệt. Phạm vi `layout` chỉ là duyệt của người dùng và kiểm tra bao hình danh nghĩa; không là phát hành chế tạo.

## Lưu trữ và khả năng khôi phục

`storage/cabinet-designs/learning.sqlite3` chứa revisions, heads, events và reviews. SQLite WAL và `BEGIN IMMEDIATE` giữ snapshot, revision đầu và nhật ký cùng giao dịch. Kiểm tra revision chặn lưu đè từ cửa sổ khác. Khóa liên tiến trình cũ vẫn bao quanh thao tác lưu từng dự án.

Các tệp `{project_id}.json` tiếp tục được ghi để tương thích và tra cứu cục bộ. Sau khi một dự án có head trong SQLite, API lấy SQLite làm nguồn chính. Nếu ghi JSON mirror bị gián đoạn, revision đã commit vẫn đọc được. Sao lưu SQLite cùng WAL bằng SQLite backup API hoặc khi đã dừng ghi; không chỉ sao chép file JSON rồi coi là có đủ lịch sử.

Dữ liệu JSON cũ được nhập vào lịch sử ở lần lưu thay đổi tiếp theo. Không tự biến thiết kế cũ thành mẫu học. Kho dữ liệu này không thay database nghiệp vụ, uploads hoặc các kết quả bóc tách đã có.

## Điều kiện hiệu lực và phạm vi cá nhân

Mẫu phải do người dùng duyệt đúng revision đã lưu. CAD phải khớp yêu cầu hãng/loại/model/cực, có front/side, đơn vị mm và tệp hình học tồn tại. Bao hình cùng tham chiếu CAD đang sử dụng phải khớp hồ sơ nguồn. Bao hình tạm và thiết kế thiếu yêu cầu bóc tách gốc bị chặn duyệt học.

Mỗi quyết định giữ fingerprint của profile và hash từng tệp geometry. Lần tra cứu kiểm lại chúng. Hồ sơ đã sửa, thu hồi, nguồn bị mất/thay đổi hoặc dự án đã xóa mềm không được dùng. Thay đổi chọn đối tượng hoặc ẩn/hiện nóc không làm mất hiệu lực hình học đã duyệt; thay đổi vị trí/kích thước thì có.

Các mẫu chỉ được tra trong dự án đang tồn tại của cùng chủ sở hữu. Một người có nhiều tủ dùng cùng lựa chọn không được tăng phiếu theo số bản sao thiết bị vật lý trong một tủ. Phạm vi duyệt chọn CAD và duyệt bố trí của cùng tủ cũng không nhân đôi phiếu xếp hạng. Không có chia sẻ tự động giữa tài khoản.

## Trạng thái phép đo

API trả số mẫu đã duyệt và fingerprint bộ nhớ. `accuracy=null` cho đến khi có kết quả đánh giá độc lập; số mẫu không được hiển thị thành tỷ lệ chính xác. Kiểm thử hồi quy xác nhận ranking đổi sau duyệt và trở về khi thu hồi, không chứng minh khả năng tổng quát trên dự án thật.

Việc học hiện áp dụng trực tiếp cho **luồng đưa thiết bị bóc tách vào tab Tủ thiết kế**. Các pipeline CAD khác chưa tự dùng bộ nhớ này. Tự động huấn luyện mô hình, kiểm định theo nhóm nguồn và rollout theo chất lượng vẫn là các bước tiếp theo trong đặc tả gốc.

## Kiểm tra hồi quy

Từ `BE_AIDE`:

```powershell
.\venv\Scripts\python.exe -m unittest scripts.test_design_learning -v
```

Bộ kiểm tra cô lập bao gồm journal trước–sau, nhập baseline cũ, xung đột revision, ghi đồng thời, lỗi JSON mirror, giới hạn chủ sở hữu, dự án không còn được phép dùng, idempotency, thu hồi, hash thay đổi, sửa vị trí, thay đổi yêu cầu, thiếu CAD và điều kiện tái sử dụng bố trí. Kiểm tra quyền route và thao tác UI cần chạy với bản backend/frontend mới.

## Dữ liệu triển khai

Backend đọc registry ở `data/design_learning/device-blocks` nếu được triển khai riêng; trong workspace dùng `AIDE/packages/cad-viewer-example/public/device-blocks`. Cần có `cad-profiles.json`, thư mục `geometry` và các shard `rows` nếu dùng liên kết mã đặt hàng tới CAD họ. Liên kết này phải có đúng dòng giá, mã, hãng, profile và tham chiếu front/side; không suy tương đương từ tên giống nhau. Nếu thiếu, matching trả cần bằng chứng thay vì chọn hình giả. Backend và frontend phải dùng cùng bộ dữ liệu profile/geometry; khi thay nguồn cần làm mới build và rà soát lại các quyết định phụ thuộc.

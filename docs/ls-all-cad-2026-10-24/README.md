# CAD LS — cập nhật và kiểm tra ngày 24/10/2026

Thư viện công khai hiện có **242 nhóm / 1.128 mặt LS**, không còn nhóm chỉ một mặt. Đã ẩn 23 nhóm một mặt vì nhận dạng mới là ứng viên, chưa chứng minh đúng cấu hình; giữ nguyên nguồn để đối chiếu. Hai mô hình cuộn dây chưa phải cụm phụ kiện hoàn chỉnh cũng được ẩn và thay bằng cụm đúng từ mô hình hãng.

## Cập nhật mới nhất: GIMAC EX/M485

Đã bổ sung **sáu mặt native / một dòng giá** cho GIMAC-1000 EX,M485 sau khi đối chiếu catalogue hãng: NO/EX là cấp chức năng, M485/ETH là giao tiếp độc lập. Kết quả hiện tại **373/517 dòng có CAD; 348 đủ sáu mặt; 25 thiếu mặt; 144 chưa có liên kết phù hợp; còn 169 gap**. [Bằng chứng và kết quả triển khai](../ls-gimac-review-2026-10-26/README.md). Các con số ở những đợt bên dưới là lịch sử.

## Rà sâu MCCB / contactor / relay ngày 26/10/2026

- [Báo cáo mới nhất](../ls-targeted-review-2026-10-26/README.md): thêm **4 hồ sơ / 8 mặt** cho năm dòng contactor DC 1a1b và hai dòng ABS1003b/1004b; kiểm tra riêng nguồn MR-8 AC/DC và GMP. Những nguồn có hai/ba mặt vẫn chưa đủ sáu mặt.
- Sửa lỗi nâng tham khảo cùng series thành đúng họ CAD; loại năm liên kết MCCB không đủ bằng chứng. Contactor tăng **61 → 66/69 dòng**, MCCB có **109/127 dòng** được ghép phù hợp; nhóm MCCB trong bảng giá bao gồm cả phụ kiện.
- Tổng sau sửa vẫn **372 liên kết / 347 đủ sáu mặt / 25 thiếu mặt / 145 chưa có CAD phù hợp**; còn **170 gap**, nhưng danh sách và bộ CAD liên kết đã thay đổi. Thư viện hiện **241 hồ sơ / 1.122 mặt**. 60 kiểm tra hồi quy đạt.

## Triển khai API ngày 26/10/2026

- Đã triển khai vào API đang chạy tại `http://127.0.0.1:8000`: cập nhật chỉ mục phục vụ tệp cho **12 hồ sơ / 58 mặt CAD** và thay lần lượt các worker của những tiến trình API hiện có. Các worker mới đã khởi tạo, health trả **200**. Không xác nhận riêng tên miền công khai bên ngoài.
- Kiểm tra HTTP có xác thực: LX/LAM trả đúng bộ sáu mặt; LA vẫn không có liên kết vì thiếu biến thể gá; BK05S-T3 2P/4P chỉ trả đúng bộ hai mặt của số cực tương ứng; cả tám mẫu MT có bộ sáu mặt trong API chi tiết giá.
- **58/58 DXF nguồn** tải qua API trả 200 và hash khớp tệp gốc. Ảnh BK05 trả 200, đã sửa lỗi 404 do thiếu bản ghi trong chỉ mục tệp. Ba mẫu tải mặc định có visibility parameter, đơn vị mm, DXF audit không lỗi; chưa kiểm tra lại chuyển trạng thái trong AutoCAD cho các bộ mới.
- 58 kiểm tra hồi quy đạt. Độ phủ giữ **372 liên kết / 347 đủ sáu mặt / 25 thiếu mặt / 145 chưa có CAD**, vẫn còn **170 gap**. Triển khai không biến nguồn chưa xác minh thành CAD được duyệt.
- [Kết quả triển khai](deployment-result-20261026.json), [kiểm tra HTTP và hash](live-api-final-20261026.json), [12 hồ sơ đã đưa vào chỉ mục](deployment-index-20261026.json). Các ghi chú “chưa triển khai” ở các đợt lịch sử bên dưới mô tả trạng thái trước lần triển khai này.

## Kết quả rà soát bổ sung SPD ngày 26/10/2026 (trước triển khai)

- Đã tải và chuyển đổi native hai tệp DWG trên trang LS BK AC của 2SK. **BK05S-T3** có đúng tiêu đề model và nhãn 2P/4P: nhập **hai hồ sơ / bốn mặt** (mặt trước theo số cực, một mặt bên dùng chung trên cùng tờ nguồn); ghép đúng hai dòng giá. Mỗi bộ vẫn thiếu sau/trái/phải/trên/dưới, không tự dựng thêm mặt hoặc đánh dấu đủ sáu mặt.
- Tệp quảng cáo **BK10,20,30,40S.dwg** lại ghi **TS250 MCCB** trong nội dung. Đã đánh dấu loại, không ghép cho SPD. Nguồn BK05 có đơn vị mm nhưng một số kích thước danh định ghi đè khác hình học; giữ nguyên tỷ lệ nguồn, yêu cầu kiểm tra kích thước lắp trước gia công.
- Tổng hiện tại: **372/517 dòng có CAD tham chiếu đúng cấu hình**, **347 đủ sáu mặt**, **25 còn thiếu mặt**, **145 chưa có CAD phù hợp**. Vẫn còn **170 gap**; thư viện **237 nhóm / 1.114 mặt**. Không tuyên bố đã hoàn tất toàn bộ CAD LS.
- [Bốn mặt và nguồn/hash](bk05s-additions-20261026.json), [kiểm tra DXF](bk05s-validation-20261026.json). 58 kiểm tra hồi quy đạt; kiểm tra API xác nhận mỗi dòng 2P/4P chỉ trả đúng bộ CAD của số cực đó. Chưa kiểm tra AutoCAD visibility động hoặc triển khai lại API cho các mặt mới.
- [Bảng xử lý từng gap JSON](remaining-gap-dispositions-20261026.json) · [CSV](remaining-gap-dispositions-20261026.csv): ghi rõ trạng thái, mặt còn thiếu, nguồn ứng viên, lý do không duyệt và bằng chứng cần bổ sung. Đây là rà soát tương thích của kho nguồn hiện có; nguồn ứng viên chưa được coi là bằng chứng đã duyệt.

## Rà soát liên kết ngày 26/10/2026 (lịch sử)

- Tìm tiếp trong danh mục tải chính hãng LS America cho Susol, Metasol MCCB, GIMAC, BK, LA63, MR-8 và MC-150; lưu kết quả nguồn trong `research-gap-20261025/`. Không dùng phụ kiện UTE/UTS UL cho dòng giá TD/TS IEC khi chưa có căn cứ tương thích.
- Sửa ưu tiên liên kết: ID dòng giá đã duyệt phải thay thế ứng viên tham khảo tìm được trước đó. Vẫn lọc hãng, phạm vi ID, số cực, cuộn và tiếp điểm trước khi áp dụng; không tự duyệt liên kết mới theo tên gần giống.
- Đối chiếu catalog MMS chính hãng trang 16/24 và nguồn STEP dùng chung LX/LA/LAM. Khôi phục đúng **hai dòng LX 1NO+1NC và LAM 1NO+1NC** với bộ CAD sáu mặt đã có. **LA vẫn là gap** vì chưa biết biến thể gá MMS-32 hay MMS-63/100; đã rút liên kết ID ứng viên khỏi hồ sơ nguồn.
- Cơ cấu STEP `AC9_50` chưa có dây/điện trở nạp trước của cụm capacitor hoàn chỉnh; chưa đưa vào dòng AC-9/AC-50. STEP DC MC-50a~100a ghi 2A2B, dòng giá yêu cầu 1A1B và không có tên cụm riêng đủ căn cứ để tách; giữ gap.
- Đợt này **không công bố hình học CAD mới**. Độ phủ tăng nhờ hai liên kết có nguồn đã xác minh: **370/517 liên kết, 347 đủ sáu mặt, 23 thiếu mặt, 147 chưa có CAD phù hợp; còn 170 gap**. Thư viện vẫn 235 nhóm / 1.110 mặt. 58 kiểm tra hồi quy đạt; chưa triển khai API đang chạy.
- [Quyết định nguồn, cấu hình và hash sáu DXF](gap-review-20261026.json), [catalog MMS trang 16](research-gap-20261025/mms-16.png), [cơ cấu gá trang 24](research-gap-20261025/mms-24.png). Script tái tạo: `scripts/finalize_ls_gap_review_20261026.py`.

## Bổ sung tiếp ngày 25/10/2026 (lịch sử)

- Thêm **48 mặt / 8 bộ STEP** chính hãng: MT-12, MT-32, MT-63 Screw, MT-95 Screw, MT-150 Screw, MT-225 Lug, MT-400 Lug và MT-800 Panel. Mỗi bộ có trước/sau/trái/phải/trên/dưới riêng, đối chiếu hướng núm chỉnh, đầu nối và mặt gá với catalog hãng; không ghép các biến thể.
- **9 dòng giá MT chuyển từ thiếu mặt sang đủ sáu mặt**. Tổng hiện tại: 517 dòng, 368 có liên kết, **345 đủ sáu mặt**, **23 còn thiếu mặt**, **149 chưa có CAD phù hợp**; còn **172 gap**. CAD họ chưa xác nhận mã đặt hàng, heater, cấp tác động hoặc cấu hình đầu nối cuối cùng của đơn hàng.
- Catalog GMP trang PDF 10–11 xác nhận 2SPST (1a1b), đầu 95/96 và 97/98. Bổ sung **6 liên kết dòng giá** vào hai bộ GMP đã nhập (GMP22-3P, GMP40-2P/3P). Các dòng này vẫn thiếu mặt; không gộp với bộ hai mặt cũ. Chưa ghép GMP22-2P vào bản vẽ có tiêu đề chỉ GMP22-3P/3PR.
- Tệp America-32501 trả catalog Meta-MEC Mini khác tiêu đề Metasol trong metadata, đã đánh dấu `rejected_content_mismatch`, không dùng làm bằng chứng. Nguồn DWG RU-0039d43c4bc97078 vẫn chưa được duyệt tỷ lệ; các bộ MT mới lấy trực tiếp STEP chính hãng riêng biệt.
- Kiểm tra 48 DXF: INSUNITS=4, AUDIT 0 lỗi / 0 sửa, hash STEP khớp, bao hình các cặp mặt đối diện nhất quán; 28 bài hồi quy giá/độ phủ đạt. Chưa kiểm tra AutoCAD hoặc tạo bộ visibility động cho các mặt mới; chưa triển khai lại API.
- [Danh sách bổ sung và dòng giá](mt-america-additions-20261025.json), [kiểm tra 48 mặt](mt-america-validation-20261025.json), [ảnh 8 bộ](mt-america-contact-sheet-20261025.png), [bằng chứng liên kết GMP](gmp-price-links-20261025.json), [catalog gốc và hash](research-2026-10-25/catalog-sources.json).

## Đợt rà soát đầu ngày 25/10/2026 (lịch sử)

- Bổ sung hai hồ sơ tham chiếu cơ khí GMP22-3P/3PR và GMP40-2P/3P/3PR: mỗi hồ sơ có trước, bên và sau từ bản vẽ native đã kiểm tra. Giữ layer/màu, loại layer kích thước DI khỏi cửa sổ trích xuất; không suy hướng trái/phải từ nhãn mặt bên chung.
- **Không thêm liên kết giá**: nguồn cơ khí chưa đủ chứng minh cấu hình tiếp điểm 1a1b của dòng giá. Không ghép mặt của hai hồ sơ hoặc biến thể khác nhau. Các dòng GMP vẫn nằm trong hàng đợi thiếu mặt.
- Chưa nhập MT-150/225/400/800 từ nguồn RU-0039d43c4bc97078: INSUNITS=0 và nhiều kích thước ghi đè khác hình học (ví dụ hình học 100, nhãn 200), chưa xác minh được tỷ lệ mm thống nhất.
- Độ phủ giá giữ nguyên **368/517**, gồm **336 đủ sáu mặt**, **32 thiếu mặt**, **149 chưa có CAD phù hợp**. Toàn bộ **181 gap** có trạng thái và lý do trong hàng đợi đã cập nhật.
- Sáu DXF mới: đơn vị mm, AUDIT 0 lỗi / 0 sửa; đã kiểm tra ảnh trích xuất. 17 kiểm tra hồi quy `scripts.test_ls_price_detail` đạt. Kiểm tra AutoCAD/download động ngày 24/10 bên dưới chỉ áp dụng cho 1.056 mặt cũ; sáu mặt tham chiếu mới chưa được kiểm tra AutoCAD hoặc tạo bộ download động.
- Bằng chứng: [nguồn và quyết định](continuation-source-review.json), [kiểm tra DXF và hash](continuation-validation.json), [ảnh sáu mặt](continuation-contact-sheet.png). Script tái tạo: `scripts/continue_ls_cad_coverage.py`. Chưa triển khai lại API đang chạy.

## Bổ sung nguồn và CAD

- Tải thêm 58 tệp từ đại diện LS tại Nga và 4 STEP từ cổng LS America; lưu tên, URL, SHA256 và cấu trúc gốc. Các tệp tải nhầm hoặc không đúng cấu hình không được ghép vào bảng giá.
- Công bố **17 nhóm / 74 mặt**: MT-12/32/63/95; MR-6/MR-8 AC/DC; MC-18a DC; bảy cụm cuộn hút; MC-32a/MC-40a DC 1NO+1NC. Những bản native chỉ có 2–3 mặt được ghi đúng số mặt, không tự bổ sung mặt suy đoán.
- Nguồn chính hãng mới cho MC-32a/MC-40a ghi rõ 3P, DC, 1A1B; đã ghép đúng hai dòng giá VDC. Không dùng bản 2A2B thay cho 1A1B.
- Giữ hình học, layer, màu và độ dày nét. Sửa các tham chiếu mặc định vật liệu/kiểu in bị treo sau nhập DXF; đối chiếu toàn bộ thuộc tính hình học trước/sau và giữ bản trước sửa.

## Đối chiếu bảng giá thực tế

| Toàn bộ dòng LS | Ghép đúng CAD | Đủ 6 mặt cùng bộ | Có CAD còn thiếu mặt | Chưa có CAD phù hợp |
|---:|---:|---:|---:|---:|
| 517 | 372 | 347 | 25 | 145 |

Số 138 cũ chỉ dựa vào liên kết ứng viên trong hồ sơ. Đối chiếu hiện dùng cùng quy tắc của API chi tiết dòng giá: đúng hãng, mã/họ, số cực, AC/DC, tiếp điểm phụ và bộ CAD. Không lấy liên kết sai để làm giảm số thiếu. Đã sửa công cụ audit gốc để các lần kiểm tra sau cũng dùng quy tắc này.

Không thay giá gốc hoặc áp dụng chiết khấu. Giá công khai phải có căn cứ chưa VAT. Bổ sung số cực theo tiêu đề 4 cực của bảng giá ACB và theo catalog MMS chính hãng; không suy số cực từ hậu tố cảm biến GMP.

Danh sách còn thiếu gồm **170 dòng cần bổ sung** (145 chưa có CAD và 25 thiếu mặt): [JSON](cad-supplement-queue.json), [CSV toàn bộ 517 dòng](pricebook-cad-coverage.csv). **Chưa hoàn tất toàn bộ bảng giá LS.**

## Giao diện và tệp tải xuống

- Hiện ngay câu “Bấm một lần chọn thiết bị, nút ▼ chọn mặt của đúng bộ CAD.” cùng nút ▼; không cần bấm chọn trước. Menu giới hạn trong mã/biến thể đang chọn.
- FE đã đẩy main, commit `70aab53c`. Build Vite riêng và kiểm tra desktop/mobile bằng dữ liệu thực đã đạt. Bước prerender của lần build chung bị lỗi thiếu dist/index.html; build riêng thành công. Đẩy Git không tự chứng minh production đã triển khai.
- Tải DXF LS mặc định tạo một block có **visibility grip thật trong AutoCAD**, các mặt lấy từ đúng bộ nguồn. 184 mặt có block động gốc được giữ nguyên byte; 176 bộ ghép mới gồm 895 thành viên đã kiểm tra AutoCAD. Có 23 thành viên trùng với nguồn động gốc; tổng hợp phủ 1.056 mặt công khai.
- Kiểm tra AutoCAD từng bộ: AUDIT **0 lỗi / 0 sửa**, đọc được CAD_FACE, chuyển được tất cả trạng thái và mỗi trạng thái chỉ có một mặt hiển thị. Không sửa tài liệu đang mở của người dùng.
- API nội bộ đã nạp bản sửa bằng cách thay từng worker; cả hai worker mới đã khởi tạo và health trả 200.
- **82 kiểm tra hồi quy đạt**, gồm liên kết dòng giá, cực/cuộn/tiếp điểm, nguồn ẩn, giá chưa VAT, giữ hình học và phân tách bộ CAD.

## Bằng chứng

- [Độ phủ chính xác theo API](strict-public-price-coverage.json)
- [Rà soát 23 nhóm một mặt](single-view-review.json)
- [Kiểm kê công khai hiện tại](current-public-inventory.json)
- [74 mặt bổ sung và hash](new-source-validation.json)
- [Sửa tham chiếu tài nguyên, giữ nguyên hình học](layer-resource-repair.json)
- [176 bộ đã kiểm tra từng trạng thái bằng AutoCAD](autocad-batch-verification.json)
- [Tổng hợp tệp tải đổi mặt](native-download-coverage.json)
- [Kiểm tra đường tải API](api-native-visibility-smoke.json)
- [Mẫu MC-32a/40a DC đủ 6 mặt — DWG](LS-MC32a-MC40a-3P-DC-1NO1NC-6mat.dwg) · [DXF](LS-MC32a-MC40a-3P-DC-1NO1NC-6mat.dxf)
- [Giao diện desktop](ls-model-selection-desktop.png) · [mobile](ls-model-selection-mobile.png)

Các nguồn chính: [LS Russia](https://lselectric-ru.com/equipment/oborudovanie-nizkogo-napryazheniya/), [LS America](https://www.lselectricamerica.com/support/download-center), thư viện tải LS Hàn Quốc và các nguồn nhà phân phối đã lưu trong hồ sơ. Các cổng không trả được CAD hoặc trả nhầm thiết bị được ghi nhận để tìm tiếp; không đưa tệp phản hồi HTML/JavaScript vào catalog như CAD.


## Bổ sung màu và nét rõ — 25/10/2026

- Bật màu mặc định cho xem trước và DXF LS tải xuống; bỏ `colored=false` ở giao diện. Những nét trung tính được phân màu: đường bao xanh cyan, vòng tròn/cung vàng cam, chữ xanh lá nhạt; giữ màu gốc có sẵn và toàn bộ đường nét.
- Chỉ chèn/đổi mã RGB trong bản xuất, không ghi lại đối tượng block động. Kiểm tra đối chiếu dữ liệu xác nhận toàn bộ phần còn lại của tệp gốc giữ nguyên, bao gồm visibility grip và trạng thái.
- Đã kiểm tra đủ 1.056 mặt LS, không thay hình học, đơn vị, layer hay độ dày nét. 85 bài kiểm tra đạt; build Vite và fixture desktop/mobile đã đạt.
- Bản mẫu đã được mở bằng AutoCAD: cấu trúc CAD đạt AUDIT 0 lỗi / 0 sửa và nhận lại các thuộc tính block động gốc sau áp màu. Chưa xác minh xong việc đặt tất cả tham số Type/Rate tùy ý vì chúng liên kết với nhau; không khẳng định kiểm tra này đã đạt.
- Cuối lần kiểm tra, AutoCAD không còn chạy và cổng API 8000 không còn lắng nghe. Vì vậy chưa xác nhận phiên API đang phục vụ đã nạp bản màu mới. Các kiểm tra API hàm trực tiếp, build và tệp vẫn đạt.
- Phần thiếu CAD không thay đổi: 149 dòng chưa có CAD phù hợp, 32 dòng còn thiếu mặt. Chưa coi catalog LS hoàn tất.

Bằng chứng: [Kiểm tra 1.056 mặt áp màu](all-ls-colour-validation.json), [ảnh mẫu có màu](colour-review/TB-74854c116c868bc4.png), [desktop](ls-colour-desktop.png), [mobile](ls-colour-mobile.png).

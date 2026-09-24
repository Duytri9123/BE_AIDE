"""Build an auditable registry and handoff guide for future CAD/AI work."""
import json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.api.v1.endpoints.cad_library import manifest
from app.services.cad.device_families import build_families
items=manifest()['items'];families=build_families(items)
selected={a for f in families for a in f['asset_ids']}
summary={'cad_files_scanned':len(items),'cad_files_with_text':sum(bool(a['recognition']['texts']) for a in items),
'usable_source_files':len(selected),'device_groups':len(families),'groups_with_known_views':sum(any(v['face']!='unknown' for v in f['views']) for f in families),
'review_only_files':len(items)-len(selected),'ai_auto_select_groups':sum(f['recognition'].get('ai_auto_select',False) for f in families)}
(ROOT/'data/cad_device_registry.json').write_text(json.dumps({'summary':summary,'devices':families,'review_only':[{'id':a['id'],'source_block':a['source_block'],'source_file':a['source_file'],'texts':a['recognition']['texts']} for a in items if a['id'] not in selected]},ensure_ascii=False,indent=2),encoding='utf8')
lines=['# Hướng dẫn AI đọc và sử dụng thư viện CAD tủ điện','',
'## Phạm vi và số lượng','',*[f'- {k}: **{v}**' for k,v in summary.items()],'',
'Các con số là file DXF nguồn và nhóm thiết bị khác nhau. Một thiết bị có thể có nhiều mặt và nhiều bản sao nguồn. Không dùng số file làm số thiết bị hoặc số mã đặt hàng. Đây là chi tiết dùng để bố trí, chưa phải một tủ đã lắp.', '',
'## Dữ liệu gốc và cách tra cứu','',
'- `cad_device_registry.json`: danh sách thiết bị đã gom, mã asset của từng mặt, tên và bằng chứng nhận dạng.',
'- `cad_text_inventory.json`: chữ TEXT/MTEXT/ATTRIB/ATTDEF đọc đệ quy trong từng file, gồm block lồng nhau. Không phải OCR; chữ vẽ bằng nét có thể không xuất hiện trong danh sách này.',
'- `catalog_cad_sync_audit.json`: ứng viên đối chiếu catalog. Trùng tên/series chưa đủ để khẳng định khớp hình học hoặc thông số.',
'- API `GET /api/v1/device-library/browse`: phân trang sau khi gom thiết bị, trả tên/hãng từ bằng chứng CAD và danh sách mặt.',
'- API `GET /api/v1/device-library/models/{id}/views`: xem đúng các mặt thuộc cùng nhóm.',
'', '## Quy tắc chọn hình để thiết kế','',
'1. Chọn đúng loại, model, số cực, thông số điện và yêu cầu lắp đặt. Không coi mã CAD:... là mã đặt hàng.',
'2. Chỉ dùng asset của mặt cần vẽ. Không dùng hình chưa xác định hướng nhìn, mặt cắt hoặc hình trục đo thay cho mặt trước/bên.',
'3. Không suy hãng từ tên file @LS, @CHINT hoặc @SCHNEIDER: các file chứa thiết bị nhiều hãng. Ưu tiên chữ trên bản vẽ; tên block là nguồn bằng chứng riêng, không phải xác minh nhà sản xuất.',
'4. Một hình có nhiều mã/rating thể hiện dùng chung hình bao hoặc cụm; phải chọn biến thể theo catalog trước khi đặt hàng. Không gộp cụm ba cầu chì thành ba mặt của một cầu chì.',
'5. `ai_auto_select=false` nghĩa là chưa được tự chọn để sinh bố trí kỹ thuật. Phải kiểm tra kích thước thực, đơn vị/tỷ lệ, hướng lắp, model và các khoảng hở. Có CAD không có nghĩa đã đủ dữ liệu thi công.',
'6. Không tự đoán hãng của bản lề/phụ kiện không có logo/mã nhà sản xuất. Có thể là chi tiết cơ khí dùng chung nhưng vẫn phải đối chiếu kích thước lắp.',
'7. Không tạo thêm CAD từ hình chữ nhật nếu đã có hình đúng; không nhân bản cùng hình để biểu diễn các thông số điện khác nhau.',
'8. Giữ các mục chưa nhận dạng ở review_only; không đưa vào danh sách tự chọn của AI. File gốc không bị xóa.',
'', '## Các lỗi đã đối chiếu và sửa','',
'- RISESUN RT18-32 1P: đế cầu chì 10×38, 32 A, 690 V. Nguồn @LS không làm thiết bị này thành LS.',
'- RISESUN RT18-32 3P: cụm ba đế đặt cạnh nhau; khác hình một cực, không phải ba hướng nhìn.',
'- CHINT RT36-00 (NT00), 160 A, AC 690 V: hai hình trước/bên của cùng cầu chì.',
'- ROBOT AP15 350 VA: ổn áp hoàn chỉnh, mặt trước có đồng hồ/công tắc/ổ ra; không phải khung vỏ tủ.',
'- EMIC EM4H03…EM4H07: mỗi mã gom các hậu tố -1/-2/-3 theo mặt trước/bên/trên đã đối chiếu bảng nguồn. Không gộp các mã EM4H khác nhau thành cùng khung.',
'- Bản lề lá 1…4: những kiểu khác nhau (4 hoặc 6 lỗ); -4-1 là hình cạnh của kiểu 4. Gạch mặt cắt trên bản lề không có nghĩa là đã lắp cả tủ.',
'- Nguồn 24 VDC là bộ nguồn AC/DC, không xếp chung với biến áp 220 VAC/24 VAC.',
'- Tu 40KVAR: tên block 40 kVAr mâu thuẫn chữ 50 kVAr trong hình. Không tự chọn công suất.',
'', '## Cách cập nhật tiếp','',
'Chạy `scripts/read_cad_evidence.py` khi nguồn CAD đổi; xem hình bên cạnh chữ trích xuất. Chỉnh các quy tắc có bằng chứng trong `app/services/cad/recognition.py`, bổ sung kiểm thử hồi quy. Chạy `scripts/build_cad_component_catalog.py`, `scripts/seed_devices_catalog.py`, `scripts/build_cad_ai_registry.py`. Khi xác minh một thuộc tính, ghi rõ tài liệu, trang/khung nguồn và phạm vi biến thể. Không đánh dấu cả thiết bị là đã xác minh chỉ vì nhận ra một hãng.',
'', '## Chỉ mục nhóm','', '| Nhóm | Số nhóm CAD |','|---|---:|']
lines += [f'| {k} | {v} |' for k,v in sorted(Counter(f['group'] for f in families).items())]
(ROOT/'data/AI_CAD_LIBRARY_GUIDE.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(summary)

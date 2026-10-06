from build_tudien_v2 import *
import xml.etree.ElementTree as ET
from datetime import datetime,timezone

c=load(OUT/'catalog.json');assets={a['id']:a for a in c['cad_assets']};errors=[]
for a in assets.values():
    for key in ['cad','preview','metadata']:
        path=(OUT/a[key]).resolve()
        if not path.is_relative_to((OUT/'dang_su_dung').resolve()) or not path.is_file():errors.append([a['id'],'bad_path',key])
    doc=ezdxf.readfile(OUT/a['cad']);ET.parse(OUT/a['preview'])
    if not len(doc.modelspace()) or doc.audit().errors:errors.append([a['id'],'bad_dxf'])
    if doc.units!=4:errors.append([a['id'],'not_mm',doc.units])
    if a['view'] in ('unknown','chua_xac_dinh'):errors.append([a['id'],'unknown_view'])
for p in c['products']:
    meta=(OUT/p['metadata']).resolve()
    if not meta.is_relative_to((OUT/'dang_su_dung').resolve()) or not meta.is_file():errors.append([p['id'],'bad_product_metadata'])
    elif load(meta)!=p:errors.append([p['id'],'stale_product_metadata'])
    if 'front' not in p['cad_by_face']:errors.append([p['id'],'no_front'])
    for face,aid in p['cad_by_face'].items():
        if aid not in assets or assets[aid]['view']!=face:errors.append([p['id'],'invalid_face'])
for f in c['forms']:
    if f['door_policy']['inner_door_equipment_cutouts'] or f['door_policy']['equipment_cutouts']:errors.append([f['id'],'precut_door'])
    if not all(f['specifications'].get(k) for k in ['height_mm','width_mm','depth_mm','sheet_thickness_source','environment','door_layers']):errors.append([f['id'],'incomplete_shell'])
    if not f.get('standard_name') or not f.get('form_code'):errors.append([f['id'],'unnamed_shell'])
if len({f['deduplication_key'] for f in c['forms']})!=len(c['forms']):errors.append(['duplicate_shell'])
for group in c['accessory_components']:
    for face,aid in group['cad_by_face'].items():
        if aid not in assets or assets[aid]['view']!=face:errors.append([group['name'],'invalid_accessory_view'])
summary=load(OUT/'active_summary.json')
report={'checked_at':datetime.now(timezone.utc).isoformat(),'active_assets':len(assets),'products':len(c['products']),
 'forms':len(c['forms']),'accessory_components':len(c['accessory_components']),'errors':errors,
 'limits':'Source CAD identity/dimensions checks, not electrical design, IP certification or manufacturing approval. No implicit resizing or automatic cutout generation.'}
save(OUT/'active_validation.json',report)
text=f'''# Catalog CAD đang sử dụng

Mở `index.html`. Thư mục sử dụng: **dang_su_dung/**. Catalog chính: **catalog.json** (schema 3).

## Kết quả hiện tại

- {len(c['forms'])} form vỏ tủ trống, có tên, mã, H × W × D, môi trường, độ dày tôn theo nguồn và số lớp cánh.
- {len(c['products'])} mã sản phẩm có thông số catalog và CAD mặt trước đủ điều kiện đối chiếu; dùng {summary['by_kind']['thiet_bi']} hình học thiết bị.
- {summary['by_kind']['phu_kien']} mặt CAD phụ kiện, trong {len(c['accessory_components'])} nhóm chi tiết/mã.
- {summary['duplicate_aliases']} bản trùng chính xác được trỏ về bản chuẩn; không dùng tên hoặc số lượng file làm bằng chứng cùng model.
- Đã kiểm kê {summary['source_assets_reviewed_structurally']} CAD của Tudien và các thư viện cũ. {summary['products_excluded']} mã catalog chưa đủ điều kiện nằm ngoài catalog sử dụng.

## Form và cánh trong

Form đang sử dụng chỉ giữ mẫu nguồn có cánh chưa khoét lỗ thiết bị; cánh trong có `equipment_cutouts=[]`. Khóa, bản lề, tai treo, gá và khe thông gió cơ khí được giữ. Mẫu đã khoét theo công trình cũ hoặc thiếu thông số không nằm trong danh sách chọn. Không bịt mọi vòng tròn một cách tự động vì có thể đó là lỗ bản lề/khóa cần giữ.

Lỗ thiết bị chỉ tạo sau khi chốt vị trí và có kích thước lỗ khoét đúng model. Chưa có module khoét lỗ tự động trong lần cập nhật này. Form dùng đúng kích thước nguồn; yêu cầu đổi kích thước bị từ chối thay vì kéo giãn tùy ý.

Quy chuẩn quản lý nội bộ: `VT-<môi trường>-<H>x<W>x<D>-<tôn>-<số lớp>L`. Đây không phải chứng nhận IEC/IP. Không có dữ liệu IP hay mác vật liệu trong nguồn thì để null, không tự ghi IP54/IP65 hoặc tiêu chuẩn chế tạo.

## CAD nào được chọn?

`products[].cad_by_face` quy định **một asset_id cho mỗi mặt**. `accessory_components[].cad_by_face` làm tương tự cho phụ kiện. Mặt chưa có trả lỗi; không dùng mặt khác, không lấy file đầu tiên của danh sách ứng viên. Cùng hình được chia sẻ giữa các dòng định mức chỉ khi dữ liệu nguồn/model/số cực/kích thước đã đối chiếu; trạng thái dùng cho bố trí nguồn không tự chứng nhận gia công.

Các trường hợp cùng tên/mặt nhưng khác hình học được chuyển sang chờ đối chiếu. Ví dụ HL036 có hai bộ hình khác kích thước nên không đưa cả hai vào bộ chọn. Hình ghi LỖ ĐỤC được phân biệt với mặt trước hoàn chỉnh của thiết bị.

Phụ kiện không rõ hãng có thể chọn bằng **mã chi tiết + mặt + kích thước nguồn** khi hình học rõ; không tự suy hãng và không tự thay thế. Mục chưa rõ bản thân chi tiết/mặt/đơn vị không được tự chọn.

## Dữ liệu nguồn và phần chờ bổ sung

- `nguon/catalog_tong_hop_truoc_loc.json`: toàn bộ catalog tổng hợp trước lọc, giữ thông số gốc.
- `cho_doi_chieu/san_pham_chua_du_dieu_kien.json`: mã thiếu CAD hoặc sai model/mặt/đơn vị/kích thước.
- `cho_doi_chieu/khong_tu_dong_su_dung.json`: form và phụ kiện bị chặn, kèm lý do.
- `geometry_aliases.json`: bản trùng → bản chuẩn; `geometry_store.json`: hình học dùng chung.
- `form_tu/index.json`, `thiet_bi/index.json`, `phu_kien/index.json`: chỉ mục đang sử dụng.
- Các thư mục CAD nguồn cũ bên ngoài `dang_su_dung` giữ để đối chiếu/tái tạo; không quét chúng để tự chọn.

## Kết nối ứng dụng

Đã thêm bộ chọn `app/services/cad/curated_library.py` và API có đăng nhập:

- `GET /api/v1/curated-library`: catalog sử dụng.
- `GET /api/v1/curated-library/product/dxf?sku=...&manufacturer=...&face=front`: chọn đúng CAD mặt.
- `GET /api/v1/curated-library/shell/<form_code>/dxf`: vỏ trống đúng mã.
- `GET /api/v1/curated-library/asset/<asset_id>/dxf`: từ chối asset ngoài catalog sử dụng.

API mới cần backend nạp lại mã. Giao diện CAD cũ và dữ liệu DB cũ chưa được tự động chuyển sang catalog mới; không coi việc có file catalog là toàn bộ luồng cũ đã dùng nó.

## Kiểm tra và tái lập

`curate_tudien_v2.py` → `validate_curated_tudien.py` → `test_curated_library.py`. Kết quả ở `active_validation.json`; `validation.json` cũ kiểm tra kho trích xuất tổng, không phải số liệu bộ đang sử dụng.

Danh sách duyệt mặt nhìn/số cực nằm tại `scripts/tudien_v2_reviewed_devices.json`. Đơn vị header một số block FOMTU ghi inch nhưng hình và thông số nguồn dùng giá trị mm: chỉ các mục được đối chiếu cụ thể có `unit_header_correction`, sửa header bản dùng mà không nhân tọa độ. Bản nguồn được giữ nguyên để đối chiếu.
'''
(OUT/'README.md').write_text(text,encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))

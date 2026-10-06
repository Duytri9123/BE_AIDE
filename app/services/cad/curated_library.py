"""Explicit selection from the CAD-only catalog; no unknown or random fallback."""
import json
from pathlib import Path

LIBRARY=Path(__file__).resolve().parents[3]/'data/thu_vien_tu_dien_v2'

def catalog():
    result=json.loads((LIBRARY/'catalog.json').read_text(encoding='utf8'))
    if result.get('schema_version')!=3:
        raise ValueError('Catalog CAD chưa hoàn tất kiểm duyệt.')
    return result

def asset_path(asset_id):
    data=catalog()
    asset=next((a for a in data['cad_assets'] if a['id']==asset_id),None)
    if asset is None:raise ValueError('CAD chưa nằm trong catalog đang sử dụng.')
    path=(LIBRARY/asset['cad']).resolve()
    if not path.is_relative_to(LIBRARY.resolve()) or not path.is_file():
        raise ValueError('Không tìm thấy CAD hợp lệ.')
    return path

def product_asset(sku,manufacturer,face='front'):
    data=catalog()
    rows=[p for p in data['products'] if p['sku']==sku and p['manufacturer'].casefold()==manufacturer.casefold()]
    if len(rows)!=1:raise ValueError('Mã/hãng chưa có một bản ghi CAD đủ điều kiện duy nhất.')
    asset_id=rows[0]['cad_by_face'].get(face)
    if not asset_id:raise ValueError('Chưa có CAD mặt yêu cầu; không dùng mặt khác thay thế.')
    return asset_id,asset_path(asset_id)

def shell(template_id,dimensions=None):
    item=next((f for f in catalog()['forms'] if f['id']==template_id or f['form_code']==template_id),None)
    if item is None:raise ValueError('Form chưa được xác nhận cánh trống và đủ thông số.')
    if item['door_policy']['inner_door_equipment_cutouts']:
        raise ValueError('Form có lỗ thiết bị sẵn trên cánh trong.')
    if dimensions and any(abs(dimensions[k]-item['specifications'][k+'_mm'])>.01 for k in ('height','width','depth')):
        raise ValueError('Form nguồn chỉ dùng đúng kích thước; chưa có ràng buộc co giãn được duyệt.')
    return item,asset_path(item['id'])

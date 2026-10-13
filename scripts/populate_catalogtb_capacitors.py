"""Separate low-voltage correction capacitors by CAD size without guessing kvar."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

BASE = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB' / 'Tụ bù'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE/'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records'] if r.get('zone') == 'C10']
assert len([r for r in ROWS if r['kind']=='view']) == 29

GROUPS = {
    '2': ('Samwha','dầu',440,'https://www.samwha.co.kr/capacitor/0301_view.asp?cate=37&sw_site=1'),
    '3': ('Samwha','khô',440,'https://www.samwha.co.kr/capacitor/0301_view.asp?cate=37&sw_site=1'),
    '4': ('Nuintek','dầu',440,'https://etinco.vn/wp-content/uploads/2025/03/catalogue-tu-bu-nuintek.pdf'),
    '5': ('Nuintek','dầu',415,'https://etinco.vn/wp-content/uploads/2025/03/catalogue-tu-bu-nuintek.pdf'),
    '6': ('Nuintek','khô',440,'https://etinco.vn/wp-content/uploads/2025/03/catalogue-tu-bu-nuintek.pdf'),
}
ROLE={'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}


def size(row):
    doc=ezdxf.readfile(SOURCE/row['cad_dxf'])
    if doc.header.get('$INSUNITS')!=4:
        return None
    ext=bbox.extents(doc.modelspace(),fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None


def fmt(number):
    return f'{number:g}'.replace('.',',')


profiles={}
for row in ROWS:
    if row['kind']!='view':
        continue
    group=row['id'].split('_cluster',1)[1].split('-',1)[0]
    brand,construction,voltage,source=GROUPS[group]
    dims=size(row)
    assert dims is not None
    type_key={'dầu':'Dau','khô':'Kho'}[construction]
    key=f'TuBu_{brand}_{type_key}_{voltage}V_C{group}_{row["id"].split("-")[-1]}'
    title=f'Tụ bù {construction} {brand} {voltage} V · hình {fmt(dims["ngang"])} × {fmt(dims["cao"])} mm'
    profiles[row['id']] = (key,{
        'nhom':'Tụ bù','ten_kieu':title,'ten_san_pham':title,
        'ban_chat':f'Tụ bù hạ áp kiểu {construction}',
        'cong_dung':'Cung cấp công suất phản kháng dung để bù tải cảm và cải thiện hệ số công suất.',
        'vi_tri_lap_dat':'Trong ngăn tụ bù, kết nối với phần tử đóng cắt và bảo vệ theo sơ đồ điện.',
        'hang_xac_nhan':None,'ma_dong_san_pham':None,
        'thong_so':{'hang_theo_nhan_ban_ve':brand,'kieu_theo_nhan_ban_ve':construction,
                   'dien_ap_theo_nhan_ban_ve_V':voltage,
                   'kich_thuoc_hinh_chieu_mm':f'{fmt(dims["ngang"])} × {fmt(dims["cao"])}'},
        'muc_do_xac_nhan':'Đã tách theo cỡ hình. Hãng, kiểu và điện áp theo nhãn cụm bản vẽ; chưa đối chiếu tem từng tụ. Dung lượng kvar, tần số và mã đặt hàng chưa xác định.',
        'nguon_tham_khao':[source],
        'lua_chon_ky_thuat':['Đối chiếu tem thiết bị để chọn dung lượng kvar, điện áp, tần số và số pha.',
                              'Kiểm tra cấu hình đóng cắt, bảo vệ, xả tụ và cuộn kháng nếu hệ thống có sóng hài.'],
        'cac_hinh_cad':[row['id']],
    })

for row in ROWS:
    chosen=profiles.get(row['id'])
    folder=(BASE/'ThietBi'/chosen[0] if chosen else BASE/'TuLieuBanVe'/'C10')/ROLE[row['kind']]/row['id']
    folder.mkdir(parents=True,exist_ok=True)
    assets={}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        if not row.get(field):
            continue
        src=(SOURCE/row[field]).resolve()
        assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
        shutil.copy2(src,folder/name)
        assets[field]=name
    info={'id':row['id'],'thiet_bi':chosen[0] if chosen else None,
          'loai_hinh':row['kind'],'ten_hinh':row['name'],
          'kich_thuoc_hinh_mm':size(row),'tep':assets}
    (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,profile in profiles.values():
    path=BASE/'ThietBi'/key/'thong_tin_thiet_bi.json'
    path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(profiles),'records':len(ROWS)},ensure_ascii=False))

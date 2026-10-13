"""Curate the A03 insulating strips and related parts by physical variant."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.addons.drawing.svg import SVGBackend

BASE = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB' / 'Phíp'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = {r['id']: r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records'] if r.get('zone') == 'A03'}
MATERIAL_SOURCE = 'https://tufnol.com/paper-laminates/kite-brand-tufnol/'
PROFILES = {}


def add(key, title, kind, purpose, position, ids, *, dimensions=None, label=None, notes=None):
    assert key.isascii() and key not in PROFILES and all(i in ROWS for i in ids)
    spec = {}
    if dimensions:
        spec['kich_thuoc_chi_tiet_mm'] = dimensions
    if label:
        spec['nhan_tren_ban_ve'] = label
    PROFILES[key] = {
        'nhom': 'Phíp', 'ten_kieu': title, 'ten_san_pham': title,
        'ban_chat': kind, 'cong_dung': purpose, 'vi_tri_lap_dat': position,
        'hang_xac_nhan': None, 'ma_dong_san_pham': None, 'thong_so': spec,
        'muc_do_xac_nhan': notes or 'Chưa xác định hãng, vật liệu cụ thể hoặc mã đặt hàng.',
        'nguon_tham_khao': [MATERIAL_SOURCE] if kind == 'Thanh đỡ cách điện' else [],
        'cac_hinh_cad': ids,
    }


STRIP_USE = 'Giữ chi tiết dẫn điện hoặc thiết bị theo vị trí lắp, đồng thời tạo khoảng cách cách điện với kết cấu tủ.'
STRIP_PLACE = 'Trong khoang phân phối hoặc khoang đấu nối, trên khung đỡ của tủ.'
strip_rows = [
    ('ThanhPhyp_JSJ270_270x35','Thanh đỡ cách điện JSJ 270-3P · 270 × 35 mm','JSJ 270-3P',
     '270 × 35',['B_2d214ca69b86']),
    ('ThanhPhyp_JSJ290_295x35','Thanh đỡ cách điện JSJ 290-4P · 295 × 35 mm','JSJ 290-4P',
     '295 × 35',['B_0892a10ece1f']),
    ('ThanhPhyp_JSJ180_180x28_5','Thanh đỡ cách điện JSJ-180 · 180 × 28,5 mm','JSJ-180',
     '180 × 28,5',['B_67629a19d082']),
    ('ThanhPhyp_EuroklasMH1_180x30','Thanh đỡ cách điện EUROKLAS MH1 · 180 × 30 mm','EUROKLAS MH1',
     '180 × 30',['B_9d37112ca669']),
    ('ThanhPhyp_EuroklasMH2_270x40','Thanh đỡ cách điện EUROKLAS MH2 · 270 × 40 mm','EUROKLAS MH2',
     '270 × 40',['B_eb2cf181996e']),
    ('ThanhPhyp_HT10D3_220x34_5','Thanh đỡ cách điện H&T 10D3 · 220 × 34,5 mm','H&T 10D3',
     '220 × 34,5',['B_449a900ec53e']),
    ('ThanhPhyp_HT10D3_500x40','Thanh đỡ cách điện H&T 10D3 · 500 × 40 mm','H&T 10D3',
     '500 × 40',['B_26ac0f5c3486']),
]
for key,title,label,dimensions,ids in strip_rows:
    add(key,title,'Thanh đỡ cách điện',STRIP_USE,STRIP_PLACE,ids,
        dimensions=dimensions,label=label,
        notes='Kích thước hình chi tiết đã xác định; nhãn trên bản vẽ chưa xác nhận được là mã hàng hoặc hãng. Vật liệu và cấp cách điện chưa xác định.')

for letter,name,id_,dimensions in [
    ('N','Thanh trung tính N','B_8ce86a6ae65d','10 × 160'),
    ('E','Thanh tiếp địa E','B_a9f51566bd67','10 × 115')]:
    add(f'Thanh{letter}_{dimensions.replace(" × ","x")}',name,'Thanh đấu nối',
        'Tập trung các dây cùng chức năng để đấu nối và phân phối.',
        'Trong khoang đấu nối, trên bộ đỡ tương ứng.',[id_],dimensions=dimensions,
        notes='Chưa xác định vật liệu, tiết diện dây tương thích và dòng cho phép.')

for name,dimensions,ids in [
    ('S25','25 × 28,9',['B_35241864a9c5','B_b3235f85f757']),
    ('S35','35 × 40,4',['B_670364b0c6b7','B_80897f043c3a']),
    ('S50','50 × 57,7',['B_bf0b060e89bb','B_e8e1e87c60ec']),
    ('S54','54 × 62,4',['B_20a4a359ccb1','B_5ee5724fc101'])]:
    add(f'SuDo_{name}',f'Sứ đỡ cách điện {name}','Trụ đỡ cách điện',
        'Đỡ chi tiết mang điện và cách ly với khung tủ.',
        'Trong khoang thanh dẫn, tại điểm bắt với khung đỡ.',ids,label=name,
        notes='Cùng nhãn có các hình chiếu với bao kích thước khác nhau; chưa xác định điện áp chịu đựng và tải cơ.')


def size(row):
    doc=ezdxf.readfile(SOURCE/row['cad_dxf'])
    if doc.header.get('$INSUNITS') != 4:
        return None
    ext=bbox.extents(doc.modelspace(),fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None


def geometry_and_preview(dxf_path, svg_path):
    doc=ezdxf.readfile(dxf_path)
    assert doc.header.get('$INSUNITS') == 4
    ext=bbox.extents(doc.modelspace(),fast=True)
    assert ext.has_data
    holes=[{'x_mm':round(e.dxf.center.x,3),'y_mm':round(e.dxf.center.y,3),
            'duong_kinh_mm':round(2*e.dxf.radius,3)}
           for e in doc.modelspace() if e.dxftype()=='CIRCLE']
    drawing=SVGBackend()
    Frontend(RenderContext(doc),drawing).draw_layout(
        doc.modelspace(),layout_properties=LayoutProperties('Model','#ffffff','#243b53',units=4,dark_background=False))
    page=Page(max(35,ext.size.x+20),max(35,ext.size.y+20))
    svg=re.sub(r'stroke: #[0-9a-fA-F]{6}','stroke: #243b53',drawing.get_string(page))
    svg_path.write_text(svg,encoding='utf-8')
    return {'don_vi':'mm','goc_chen_dxf_mm':{'x':0,'y':0},
            'bao_hinh_mm':{'min_x':round(ext.extmin.x,3),'min_y':round(ext.extmin.y,3),
                           'max_x':round(ext.extmax.x,3),'max_y':round(ext.extmax.y,3)},
            'tam_bao_hinh_mm':{'x':round(ext.center.x,3),'y':round(ext.center.y,3)},
            'lo_tron':holes}


selected = {id_:key for key,p in PROFILES.items() for id_ in p['cac_hinh_cad']}
assert len(selected) == sum(len(p['cac_hinh_cad']) for p in PROFILES.values())
product_root=BASE/'ThietBi'
if product_root.exists():
    assert product_root.resolve().is_relative_to(BASE.resolve())
    assert {p.name for p in product_root.rglob('*') if p.is_file()} <= {
        'thong_tin_thiet_bi.json','thong_tin.json','ban_ve.dxf','xem_truoc.svg'}
    shutil.rmtree(product_root)
role={'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}
for id_,row in ROWS.items():
    key=selected.get(id_)
    folder=(BASE/'ThietBi'/key if key else BASE/'TuLieuBanVe'/'A03')/role[row['kind']]/id_
    folder.mkdir(parents=True,exist_ok=True)
    assets={}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        if not row.get(field):
            continue
        source_file=(SOURCE/row[field]).resolve()
        assert source_file.is_relative_to(SOURCE.resolve()) and source_file.is_file()
        shutil.copy2(source_file,folder/name)
        assets[field]=name
    geom=geometry_and_preview(folder/'ban_ve.dxf',folder/'xem_truoc.svg') if key else None
    info={'id':id_,'thiet_bi':key,'loai_hinh':row['kind'],
          'ten_hinh':row['name'],'tep':assets,'kich_thuoc_hinh_mm':size(row)}
    if geom:
        info['hinh_hoc_lap_dat']=geom
        if key.startswith(('ThanhN_','ThanhE_')):
            PROFILES[key]['thong_so']['so_lo_tron_tren_cad']=len(geom['lo_tron'])
            PROFILES[key]['thong_so']['nhom_lo_theo_duong_kinh_mm']='; '.join(
                f'Ø{d:g}: {sum(h["duong_kinh_mm"]==d for h in geom["lo_tron"])} lỗ'
                for d in sorted({h['duong_kinh_mm'] for h in geom['lo_tron']}))
    (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,profile in PROFILES.items():
    (BASE/'ThietBi'/key/'thong_tin_thiet_bi.json').write_text(
        json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(PROFILES),'attached_drawings':len(selected),'records':len(ROWS)},ensure_ascii=False))

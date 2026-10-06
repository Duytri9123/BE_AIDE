"""Curate C09 terminal blocks without promoting repeated CAD instances to products."""
from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
TARGET = ROOT / 'Cầu đấu'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']
        if r.get('zone') == 'C09']
assert len(ROWS) == 228

UK_SOURCE = 'https://www.delixi-electric.com/en/u/cms/delixi/202406/04160101am05.pdf'
TOSUN_SOURCE = 'https://www.tosunlux.com/electrical-accessories/terminal-block/uk-terminal-block.html'
CTS_SOURCE = 'https://www.altechcorp.com/Blocks/TerminalBlocks_2016_web.pdf'
HYT_SOURCE = 'https://www.propluscorp.co.th/Downloads/Catalog/HUNYOUNGNUX/HANYOUNG-NUX-Catalog-Product-Guide-2023.pdf'

def dimensions(row):
    doc = ezdxf.readfile(SOURCE / row['cad_dxf'])
    if doc.header.get('$INSUNITS') != 4:
        return None
    ext = bbox.extents(doc.modelspace(), fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None

VIEW_ROWS = [r for r in ROWS if r['kind'] == 'view']
assert len(VIEW_ROWS) == 174
SIZES = {r['id']:dimensions(r) for r in VIEW_ROWS}

def family(row):
    name = row['name'].upper().replace('_','-')
    if name == 'UK3N': return 'UK3N'
    if name == 'CHAN TER': return 'ChanTer'
    if name in {'CTS25','CTS6','CTS4'}: return name
    if re.fullmatch(r'TB-\d+P-\d+A',name): return name.replace('-','_')
    if re.fullmatch(r'CD-\d+P-\d+A',name): return name.replace('-','_')
    if re.fullmatch(r'HYT-?\d+',name): return name.replace('-','')
    return None

BY_FAMILY = defaultdict(list)
for row in VIEW_ROWS:
    key = family(row)
    if key: BY_FAMILY[key].append(row)
assert len(BY_FAMILY) == 37

def profile(key, rows):
    first = rows[0]
    name = first['name'].upper().replace('_','-')
    size = SIZES[first['id']]
    details = {'nhan_tren_hinh':name,'so_hinh_cung_nhan':len(rows)}
    if size: details['kich_thuoc_hinh_dai_dien_mm'] = f"{size['ngang']} × {size['cao']}"
    sources = []
    model = None
    status = 'Mã và trị số lấy từ tên hình; chưa xác định hãng hoặc thông số đặt hàng.'
    if key == 'UK3N':
        display = 'Cầu đấu đơn UK3N'
        kind = 'Cầu đấu xuyên dây một tầng lắp ray'
        use = 'Nối hai đầu dây của một mạch qua cọc kẹp vít.'
        place = 'Trên ray DIN trong ngăn đấu nối dây điều khiển hoặc tín hiệu.'
        model = 'UK3N'
        details['so_ban_ve_6x42_5_mm'] = sum(SIZES[r['id']]=={'ngang':6.0,'cao':42.5} for r in rows)
        details['so_hinh_phong_120_phan_tram'] = sum(SIZES[r['id']]=={'ngang':7.2,'cao':51.0} for r in rows)
        status = 'Hình 7,2 × 51 mm là bản phóng 120% của hình 6 × 42,5 mm, không tách thành cỡ sản phẩm khác. Hãng chưa xác định.'
        details['tham_khao_UK3N_TOSUN'] = '32 A · 800 V · dây mềm đến 2,5 mm²; chưa gán cho bản vẽ'
        sources = [UK_SOURCE,TOSUN_SOURCE]
    elif key == 'ChanTer':
        display = 'Chặn cuối dãy cầu đấu'
        kind = 'Phụ kiện cố định cầu đấu'
        use = 'Giữ dãy cầu đấu không trượt trên ray.'
        place = 'Ở đầu hoặc cuối dãy cầu đấu lắp trên ray DIN.'
        status = 'CHAN Ter là tên hình phụ kiện; chưa xác định mã đặt hàng.'
    elif key.startswith('CTS'):
        display = f'Cầu đấu đơn {name}'
        kind = 'Cầu đấu xuyên dây một tầng lắp ray'
        use = 'Nối hai đầu dây qua cọc kẹp vít.'
        place = 'Trên ray DIN trong ngăn đấu nối.'
        model = name
        sources = [CTS_SOURCE]
        status = 'Tên CTS ghi trên hình; Altech có dòng CTS cùng chức năng, chưa xác nhận đúng hãng hoặc mã hậu tố.'
    elif key.startswith('HYT'):
        display = f'Dãy cầu đấu HYT · nhãn {name}'
        kind = 'Dãy cầu đấu bắt vít'
        use = 'Phân phối hoặc nối nhiều dây trên cùng một dãy cọc.'
        place = 'Trong ngăn đấu nối của tủ điện.'
        model = name
        sources = [HYT_SOURCE]
        status = 'Nhãn HYT ghi trên hình; chưa xác nhận hãng và thông số điện của đúng biến thể.'
        if name in {'HYT-203','HYT-204'}:
            details['tham_khao_Hanyoung_Nux'] = '20 A · '+('3 cực' if name=='HYT-203' else '4 cực')+'; chưa xác nhận đúng sản phẩm trong hình'
    else:
        m = re.fullmatch(r'(TB|CD)-(\d+)P-(\d+)A',name)
        assert m
        series, poles, amps = m.groups()
        display = f'Dãy cầu đấu {series} · {poles} cực · nhãn {amps} A'
        kind = 'Dãy cầu đấu nhiều cực bắt vít'
        use = 'Tạo các điểm nối dây cách điện theo từng cực.'
        place = 'Trong ngăn đấu nối hoặc phân phối của tủ điện.'
        details.update({'so_cuc_theo_nhan_hinh':int(poles),'dong_A_theo_nhan_hinh':int(amps)})
        status = 'Số cực và trị số A ghi trong tên hình; chưa đối chiếu nhãn sản phẩm hoặc catalogue hãng.'
    return {'nhom':'Cầu đấu','ten_kieu':display,'ten_san_pham':display,'ban_chat':kind,
            'cong_dung':use,'vi_tri_lap_dat':place,'hang_xac_nhan':None,
            'ma_dong_san_pham':model,'thong_so':details,'muc_do_xac_nhan':status,
            'nguon_tham_khao':sources,'cac_hinh_cad':[first['id']],
            'so_hinh_lap_lai':len(rows)}

PROFILES = {key:profile(key,rows) for key,rows in BY_FAMILY.items()}
REPRESENTATIVES = {p['cac_hinh_cad'][0]:key for key,p in PROFILES.items()}
assert len(REPRESENTATIVES) == len(PROFILES) == 37

ROLE = {'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}
for row in ROWS:
    key = REPRESENTATIVES.get(row['id'])
    base = TARGET / ('ThietBi' if key else 'TuLieuBanVe') / (key if key else 'C09')
    folder = base / ROLE[row['kind']] / row['id']
    folder.mkdir(parents=True,exist_ok=True)
    assets = {}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        if not row.get(field): continue
        src = (SOURCE / row[field]).resolve()
        assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
        shutil.copy2(src,folder/name)
        assets[field] = name
    info = {'id':row['id'],'thiet_bi':key,'loai_hinh':row['kind'],
            'ten_hinh':row['name'],'tep':assets}
    if row['kind']=='view': info['kich_thuoc_hinh_mm'] = SIZES[row['id']]
    (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,data in PROFILES.items():
    (TARGET/'ThietBi'/key/'thong_tin_thiet_bi.json').write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(PROFILES),'representative_views':len(REPRESENTATIVES),
                  'source_views':len(VIEW_ROWS),'context_records':len(ROWS)-len(REPRESENTATIVES),
                  'uk3n_instances':len(BY_FAMILY['UK3N'])},ensure_ascii=False))

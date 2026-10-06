"""Build device profiles for the C05 control-device drawing region."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
TARGET = ROOT / 'Bộ điều khiển' / 'ThietBi'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']
        if r.get('zone') == 'C05' and r['kind'] == 'view']
assert len(ROWS) == 20

def profile(key, name, kind, use, place, ids, *, brand=None, model=None, specs=None,
            status='Chưa xác định hãng và mã thiết bị.', sources=()):
    return key, {'nhom':'Bộ điều khiển', 'ten_kieu':name, 'ten_san_pham':name,
                 'ban_chat':kind, 'cong_dung':use, 'vi_tri_lap_dat':place,
                 'hang_xac_nhan':brand, 'ma_dong_san_pham':model,
                 'thong_so':specs or {}, 'muc_do_xac_nhan':status,
                 'nguon_tham_khao':list(sources), 'cac_hinh_cad':ids}

PHASE_USE = 'Giám sát mất pha, sai thứ tự pha hoặc điện áp bất thường và đưa tín hiệu đến mạch điều khiển.'
PHASE_PLACE = 'Trong ngăn điều khiển, đầu vào lấy tín hiệu từ lưới ba pha; tiếp điểm ra nối mạch bảo vệ.'
DRIVE_USE = 'Điều chỉnh tần số và điện áp cấp cho động cơ để điều khiển tốc độ.'
DRIVE_PLACE = 'Trong ngăn động lực, sau thiết bị bảo vệ nguồn và trước động cơ.'
ATS_USE = 'Theo dõi hai nguồn và phát lệnh chuyển nguồn theo cấu hình hệ thống.'
ATS_PLACE = 'Trong tủ chuyển nguồn tự động, nối mạch đo nguồn và mạch điều khiển đóng cắt.'

PROFILES = dict([
    profile('BaoVePha_Ray', 'Rơ le giám sát pha · dạng ray hẹp', 'Rơ le bảo vệ pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V001']),
    profile('BaoVePha_MatKim', 'Bộ giám sát pha · mặt hiển thị kim', 'Bộ giám sát pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V002']),
    profile('BaoVePha_BaNum', 'Bộ giám sát pha · ba núm chỉnh', 'Bộ giám sát pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V003']),
    profile('BaoVePha_RayBaNum', 'Rơ le giám sát pha · ba núm chỉnh', 'Rơ le bảo vệ pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V004']),
    profile('BaoVePha_MX100', 'Thiết bị điều khiển MX100', 'Thiết bị điều khiển',
            'Chức năng cụ thể chưa xác định từ hình.', 'Trong ngăn điều khiển.',
            ['C05_cluster1-V005'], specs={'ky_hieu_tren_hinh':'MX100'},
            status='MX100 là nhãn của hình; chưa xác định hãng, chức năng và mã đặt hàng.'),
    profile('BaoVePha_HienThiSo', 'Bộ giám sát pha · màn hình số', 'Bộ giám sát pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V006']),
    profile('BaoVePha_MatVaLung', 'Bộ giám sát pha · hai mặt hình', 'Bộ giám sát pha', PHASE_USE,
            PHASE_PLACE, ['C05_cluster1-V007', 'C05_cluster1-V008'],
            status='Hai hình thể hiện hai mặt của cùng kiểu thiết bị; chưa xác định hãng và mã.'),
    profile('OnAp_DangNgang', 'Bộ ổn áp · thân ngang', 'Thiết bị ổn áp',
            'Điều chỉnh điện áp cấp cho tải trong giới hạn của thiết bị.',
            'Trên đường cấp nguồn cho phụ tải.', ['C05_cluster2-V001']),
    profile('OnAp_DangDung', 'Bộ ổn áp · thân đứng', 'Thiết bị ổn áp',
            'Điều chỉnh điện áp cấp cho tải trong giới hạn của thiết bị.',
            'Trên đường cấp nguồn cho phụ tải.', ['C05_cluster2-V002']),
    profile('BienTan_LS', 'Biến tần LS Electric', 'Biến tần điều khiển động cơ', DRIVE_USE,
            DRIVE_PLACE, ['C05_cluster3-V001'], brand='LS Electric',
            status='Nhận diện được logo LS; chưa xác định dòng, công suất và điện áp.',
            sources=['https://www.ls-electric.com/jp/product/category/CCC006']),
    profile('BienTan_KieuBT75', 'Biến tần · kiểu BT 7.5', 'Biến tần điều khiển động cơ', DRIVE_USE,
            DRIVE_PLACE, ['C05_cluster3-V002'], specs={'ky_hieu_tren_hinh':'BT 7.5'},
            status='BT 7.5 là nhãn hình; chưa đủ căn cứ xác nhận công suất 7,5 kW.'),
    profile('BienTan_DangDung', 'Biến tần · thân đứng', 'Biến tần điều khiển động cơ', DRIVE_USE,
            DRIVE_PLACE, ['C05_cluster3-V003']),
    profile('BienTan_BangPhim', 'Biến tần · bảng phím tích hợp', 'Biến tần điều khiển động cơ', DRIVE_USE,
            DRIVE_PLACE, ['C05_cluster3-V004']),
    profile('ATS_SoDoMat', 'Bộ điều khiển ATS · mặt sơ đồ', 'Bộ điều khiển chuyển nguồn', ATS_USE,
            ATS_PLACE, ['C05_cluster4-V001']),
    profile('ATS_ManHinh', 'Bộ điều khiển ATS · màn hình và phím', 'Bộ điều khiển chuyển nguồn', ATS_USE,
            ATS_PLACE, ['C05_cluster4-V002']),
    profile('ATS_SoDoNguon', 'Bộ điều khiển ATS · sơ đồ hai nguồn', 'Bộ điều khiển chuyển nguồn', ATS_USE,
            ATS_PLACE, ['C05_cluster4-V003']),
    profile('TuBu_MatSo', 'Bộ điều khiển tụ bù · mặt hiển thị số', 'Bộ điều khiển hệ số công suất',
            'Đóng cắt từng cấp tụ bù theo hệ số công suất đo được.',
            'Trên cửa tủ tụ bù; đầu vào đo dòng và điện áp, đầu ra điều khiển contactor cấp tụ.',
            ['C05_cluster5-V001']),
    profile('TuBu_APFC12', 'Bộ điều khiển tụ bù APFC · 12 cấp', 'Bộ điều khiển hệ số công suất',
            'Đóng cắt tối đa 12 cấp tụ bù theo hệ số công suất đo được.',
            'Trên cửa tủ tụ bù; đầu ra điều khiển từng cấp tụ.',
            ['C05_cluster5-V002'], specs={'so_cap_theo_nhan_hinh':12},
            status='Hình ghi APFC(12STEP-DELAB); chưa xác định DE-LAB là hãng hay tên bản vẽ.'),
    profile('DSE8610_Candidate', 'Bộ điều khiển máy phát · ứng viên DSE8610',
            'Bộ điều khiển hòa đồng bộ máy phát',
            'Giám sát, khởi động và chia tải giữa nhiều máy phát khi cấu hình phù hợp.',
            'Trên mặt tủ điều khiển máy phát hoặc tủ hòa đồng bộ.',
            ['C05_cluster5-V003'], specs={'dong_ung_vien':'DSE8610'},
            status='Tên hình ghi DSE8610; chưa xác nhận mã trên mặt thiết bị. Hình dạng cần đối chiếu trước khi đặt hàng.',
            sources=['https://www.deepseaelectronics.com/genset/load-sharing-synchronising-control-modules/dse8610']),
])

ID_MAP = {id_:key for key,p in PROFILES.items() for id_ in p['cac_hinh_cad']}
assert len(ID_MAP) == len(ROWS) == 20

for row in ROWS:
    key = ID_MAP[row['id']]
    folder = TARGET / key / 'HinhChieu' / row['id']
    folder.mkdir(parents=True, exist_ok=True)
    assets = {}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        src = (SOURCE / row[field]).resolve()
        assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
        shutil.copy2(src,folder/name)
        assets[field] = name
    doc = ezdxf.readfile(folder/'ban_ve.dxf')
    ext = bbox.extents(doc.modelspace(),fast=True)
    size = {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data and doc.header.get('$INSUNITS') == 4 else None
    (folder/'thong_tin.json').write_text(json.dumps({
        'id':row['id'],'thiet_bi':key,'loai_hinh':'view','ten_hinh':row['name'],
        'kich_thuoc_hinh_mm':size,'tep':assets},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,p in PROFILES.items():
    (TARGET/key/'thong_tin_thiet_bi.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(PROFILES),'drawings':len(ID_MAP)},ensure_ascii=False))

"""Build measurement-device profiles from the A01 and C04 drawing inventory."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

BASE = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
TARGET = BASE / 'ThietBiDoLuongHienThi'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']
        if r.get('zone') in {'A01', 'C04'}]
assert len(ROWS) == 81

EMIC_CV = 'https://emic.com.vn/vn/cong-to-dien-1-pha-co-khi-kieu-cv_p9721.html'
EMIC_CE = 'https://emic.com.vn/vn/cong-to-dien-tu-1-pha-2-day-ce-18g_p9718.html'
SCHNEIDER_PM = 'https://www.se.com/ch/de/product-range/917-pm700/'
SCHNEIDER_PM_END = 'https://www.se.com/uk/en/faqs/FA264122/'

def profile(name, kind, use, location, ids, *, brand=None, code=None, facts=None,
            selection=None, status='Chưa xác định mã đặt hàng chính xác', sources=None):
    return dict(ten_kieu=name, ten_san_pham=name, ban_chat=kind, cong_dung=use,
                vi_tri_lap_dat=location, hang_xac_nhan=brand, ma_dong_san_pham=code,
                thong_so=facts or {}, lua_chon_ky_thuat=selection or [],
                muc_do_xac_nhan=status, nguon_tham_khao=sources or [], cac_hinh_cad=ids)

meter_use = 'Đo và ghi điện năng tiêu thụ kWh của mạch điện.'
meter_place = 'Tại ngăn công tơ hoặc tủ đo đếm của lộ điện tương ứng.'
analog_place = 'Gắn trên mặt tủ điện để người vận hành theo dõi tại chỗ.'
PROFILES = {
 'Holley_DongHoKWh': profile('Công tơ Holley', 'Công tơ điện năng', meter_use, meter_place,
     ['A01_cluster2-V001'], brand='Holley', selection=['Kiểm tra số pha, kiểu đấu trực tiếp hoặc qua CT, dòng và điện áp định mức.'],
     status='Xác định hãng từ chữ trên bản vẽ; chưa có mã model.'),
 'EMIC_CV131_CV141_NapDai': profile('Công tơ cơ 1 pha CV131/CV141, nắp dài', 'Công tơ cơ 1 pha 2 dây', meter_use,
     meter_place, ['A01_cluster3-V001','A01_cluster3-V002'], brand='EMIC', code='CV131/CV141',
     facts={'so_pha':1,'so_day':2,'dien_nang':'hữu công kWh'},
     selection=['Phân biệt CV131 và CV141 theo nhãn máy; chọn dòng và cấp chính xác của đúng biến thể.'],
     status='Mã dòng và kiểu nắp đọc từ nhãn cụm; chưa phân biệt được model của từng hình.', sources=[EMIC_CV]),
 'EMIC_CV130_CV140_NapNgan': profile('Công tơ cơ 1 pha CV130/CV140, nắp ngắn', 'Công tơ cơ 1 pha 2 dây', meter_use,
     meter_place, ['A01_cluster4-V001','A01_cluster4-V002'], brand='EMIC', code='CV130/CV140',
     facts={'so_pha':1,'so_day':2,'dien_nang':'hữu công kWh'},
     selection=['Đối chiếu kích thước và nắp đấu dây trước khi chọn; tỷ số và dòng định mức theo đúng biến thể.'],
     status='Mã dòng và kiểu nắp đọc từ nhãn cụm; chưa phân biệt được model của từng hình.', sources=[EMIC_CV]),
 'EMIC_CV130_CV140_NapDai': profile('Công tơ cơ 1 pha CV130/CV140, nắp dài', 'Công tơ cơ 1 pha 2 dây', meter_use,
     meter_place, ['A01_cluster5-V001','A01_cluster5-V002'], brand='EMIC', code='CV130/CV140',
     facts={'so_pha':1,'so_day':2,'dien_nang':'hữu công kWh'},
     selection=['Đối chiếu kích thước và nắp đấu dây trước khi chọn; tỷ số và dòng định mức theo đúng biến thể.'],
     status='Mã dòng và kiểu nắp đọc từ nhãn cụm; chưa phân biệt được model của từng hình.', sources=[EMIC_CV]),
 'EMIC_CongToCo3P': profile('Công tơ cơ 3 pha EMIC', 'Công tơ cơ 3 pha', meter_use,
     meter_place, ['A01_cluster6-V001','A01_cluster6-V002','A01_cluster6-V003'], brand='EMIC',
     facts={'so_pha':3}, selection=['Xác định lưới 3 pha 3 dây hay 4 dây, đấu trực tiếp hay qua CT và tỷ số CT.'],
     status='DK3P là nhãn hình, chưa đủ căn cứ xem là mã sản phẩm.'),
 'EMIC_CongToDienTu1P': profile('Công tơ điện tử 1 pha EMIC', 'Công tơ điện tử 1 pha', meter_use,
     meter_place, ['C04_cluster2-V001'], brand='EMIC', facts={'so_pha':1,'so_day':2},
     selection=['Đối chiếu mã máy trước khi chọn kiểu truyền thông, dòng định mức và cấp chính xác.'],
     status='Cùng loại với dòng CE; hình chưa xác nhận mã CE-18.', sources=[EMIC_CE]),
 'EMIC_CongToDienTu3P': profile('Công tơ điện tử 3 pha EMIC', 'Công tơ điện tử 3 pha', meter_use,
     meter_place, ['C04_cluster2-V002'], brand='EMIC', facts={'so_pha':3},
     selection=['Xác định 3 pha 3 dây/4 dây, trực tiếp/qua CT, giao tiếp và cấp chính xác.'],
     status='Xác định họ thiết bị; chưa có mã model.'),
 'EMIC_CongToCo1P': profile('Công tơ cơ 1 pha EMIC', 'Công tơ cơ 1 pha 2 dây', meter_use,
     meter_place, ['C04_cluster3-V001','C04_cluster3-V002','C04_cluster3-V003'], brand='EMIC',
     facts={'so_pha':1,'so_day':2,'dien_nang':'hữu công kWh'},
     selection=['Chọn dòng định mức và cấu hình đấu dây theo nhãn máy.'],
     status='Các hình liên quan một họ công tơ; chưa xác nhận mã của từng hình.', sources=[EMIC_CV]),
 'Schneider_PM710': profile('Schneider PowerLogic PM710', 'Đồng hồ đo điện đa năng 3 pha',
     'Giám sát điện áp, dòng, công suất, điện năng và chất lượng điện cơ bản.',
     'Gắn trên mặt tủ điện; ngõ dòng nhận tín hiệu từ CT và giao tiếp RS-485 Modbus.',
     ['C04_cluster4-V001'], brand='Schneider Electric', code='PM710',
     facts={'so_pha':3,'mat_truoc_mm':'96 × 96','truyen_thong':'RS-485 Modbus',
            'ngo_vao_dong_A':'CT thứ cấp 1 A hoặc 5 A','trang_thai':'Ngừng kinh doanh từ 2015'},
     selection=['Dùng khi thay thế thiết bị hiện có; với thiết kế mới chọn dòng PM hiện hành tương đương.'],
     status='Mã PM710 ghi rõ trên hình; thông số đối chiếu tài liệu hãng.',
     sources=[SCHNEIDER_PM,SCHNEIDER_PM_END]),
 'DongHoDienTuKhac': profile('Đồng hồ đo điện kỹ thuật số', 'Đồng hồ đo điện gắn tủ',
     'Hiển thị các đại lượng điện của mạch để theo dõi vận hành.', analog_place,
     ['C04_cluster4-V002','C04_cluster4-V003','C04_cluster4-V004'],
     selection=['Xác định đại lượng đo, số pha, cấp điện áp, đầu vào CT và truyền thông trước khi chọn model.'],
     status='Số 1232 và các mã *U là tên block; chưa chứng minh được là mã thương mại.'),
 'VonKeKim': profile('Vôn kế kim gắn tủ', 'Đồng hồ đo điện áp analog',
     'Hiển thị điện áp tại vị trí đo trên thang kim.', analog_place,
     ['C04_cluster5-V001'],
     selection=['Chọn dải đo và loại điện áp phù hợp; khi đo nhiều pha cần công tắc chuyển mạch.'],
     status='Chưa xác nhận hãng và mã; số trên mặt số chỉ là thang hiển thị.'),
 'Omega_BE-96_500V': profile('Omega BE-96, vôn kế 0–500 V', 'Vôn kế kim AC gắn tủ',
     'Hiển thị điện áp xoay chiều tại vị trí đo trên thang kim.', analog_place,
     ['C04_cluster5-V010'], brand='Omega', code='BE-96',
     facts={'dai_do':'0–500 V AC','mat_truoc_mm':'96 × 96'},
     selection=['Chọn điểm đo và công tắc chuyển mạch điện áp theo sơ đồ tủ.'],
     status='Nhãn Omega BE-96 và thang 500 V đọc trên mặt đồng hồ; chưa có mã đặt hàng đầy đủ.'),
 'AmpeKeKim': profile('Ampe kế kim gắn tủ', 'Đồng hồ đo dòng điện analog',
     'Hiển thị dòng điện tại vị trí đo trên thang kim.', analog_place,
     ['C04_cluster5-V004'], selection=['Chọn dải chia độ tương ứng tỷ số CT và dòng thứ cấp 1 A/5 A.'],
     status='Chưa xác nhận hãng và mã.'),
 'ChuyenMachVon': profile('Công tắc chọn điện áp', 'Công tắc chuyển mạch đo điện áp',
     'Chọn cặp pha hoặc pha–trung tính đưa tới một vôn kế.', 'Gắn trên mặt tủ đo lường, nối trước vôn kế.',
     ['C04_cluster5-V002','C04_cluster5-V008'],
     selection=['Chọn số vị trí và sơ đồ tiếp điểm đúng với hệ 3 pha 3 dây/4 dây.'],
     status='Chưa xác nhận mã đặt hàng.'),
 'ChuyenMachAmpe': profile('Công tắc chọn dòng điện', 'Công tắc chuyển mạch đo dòng',
     'Chọn một trong các pha đưa tới ampe kế qua CT.', 'Gắn trên mặt tủ đo lường, nối sau các CT.',
     ['C04_cluster5-V003','C04_cluster5-V009'],
     selection=['Chọn loại dùng cho mạch CT, số vị trí và tiếp điểm bảo đảm không hở thứ cấp CT.'],
     status='Chưa xác nhận mã đặt hàng.'),
 'CongTacOnOff': profile('Công tắc xoay ON/OFF', 'Công tắc điều khiển hai vị trí',
     'Đóng/ngắt mạch điều khiển theo thao tác tại mặt tủ.', 'Gắn trên mặt tủ điều khiển.',
     ['C04_cluster5-V011'], selection=['Chọn số cực, cấu hình tiếp điểm, dòng và điện áp tiếp điểm.'],
     status='Chưa xác nhận mã đặt hàng; không phải đồng hồ đo.'),
 'DongHoKimNho': profile('Đồng hồ kim loại nhỏ', 'Đồng hồ chỉ thị analog gắn tủ',
     'Hiển thị một đại lượng điện tại chỗ.', analog_place,
     ['C04_cluster6-V001','C04_cluster6-V002','C04_cluster6-V003'],
     selection=['Đọc ký hiệu V/A và thang đo trước khi chọn thiết bị tương ứng.'],
     status='Hình trước và hình bên cùng một loại; chưa xác nhận hãng, thang đo hoặc model.'),
}

# Series specifications are published options, not values confirmed for each
# individual drawing or a particular meter in service.
CV_OPTIONS = {'dien_ap_dinh_muc_V':'110, 120, 220, 230 hoặc 240',
              'tan_so_Hz':'50 hoặc 60',
              'dong_dinh_muc_A':'3(9), 3(12), 5(6), 5(15), 5(20), 10(30), 10(40), 15(60), 20(80), 30(90) hoặc 40(120)',
              'cap_chinh_xac':'1 hoặc 2'}
for key in ('EMIC_CV131_CV141_NapDai','EMIC_CV130_CV140_NapNgan',
            'EMIC_CV130_CV140_NapDai','EMIC_CongToCo1P'):
    PROFILES[key]['thong_so'].update(CV_OPTIONS)
    PROFILES[key]['ghi_chu_thong_so'] = 'Các mức trên là tùy chọn của dòng CV; cần kiểm tra nhãn từng công tơ để chọn đúng biến thể.'

PROFILES['EMIC_CongToCo3P']['ma_dong_san_pham'] = 'MV'
PROFILES['EMIC_CongToCo3P']['thong_so'].update({
    'so_day_tuy_chon':'3 hoặc 4', 'dien_nang':'hữu công kWh hoặc vô công kvarh',
    'tan_so_Hz':'50 hoặc 60', 'cap_chinh_xac':'1 hoặc 2',
    'dong_dinh_muc_A':'1; 5(6); 5(10); 5(20); 10(20); 10(40); 20(40); 20(80); 25(50); 30(60); 30(90); 50(100)',
    'dien_ap_3p4d_V':'57,8/100; 63,5/110; 120/208; 127/220; 133/230; 230/400; 240/415',
    'dien_ap_3p3d_V':'100; 110; 120; 208; 210; 220; 230; 240; 380; 400; 415'})
PROFILES['EMIC_CongToCo3P']['nguon_tham_khao'] = ['https://emic.com.vn/vn/cong-to-dien-3-pha-co-khi']
PROFILES['EMIC_CongToCo3P']['ghi_chu_thong_so'] = 'Thông số là các biến thể của dòng MV; hình chưa xác định biến thể cụ thể.'

PROFILES['Schneider_PM710']['thong_so'].update({
    'dien_ap_dinh_muc':'Theo sơ đồ đấu và biến thể PM710',
    'dai_do':'V, A, kW, kVA, kvar, PF, Hz, kWh, THD',
    'do_sau_lap_dat_mm':'khoảng 50'})
PROFILES['Schneider_PM710']['ghi_chu_thong_so'] = 'Cần cài tỷ số CT/PT đúng với hệ thống; kiểm tra ngõ vào của đúng phiên bản PM710.'

PROFILES['VonKeKim']['thong_so'] = {'thang_hien_thi':'0–500 V','kieu_hien_thi':'kim analog'}
PROFILES['VonKeKim']['ghi_chu_thong_so'] = 'Thang chia đọc trên mặt hiển thị; chưa xác nhận cấp chính xác hay kiểu điện áp của sản phẩm.'
PROFILES['AmpeKeKim']['thong_so'] = {'thang_hien_thi':'0–500 A','kieu_hien_thi':'kim analog'}
PROFILES['AmpeKeKim']['ghi_chu_thong_so'] = 'Thang chia đọc trên mặt hiển thị; phải xác định tỷ số CT tương ứng trước khi sử dụng.'
PROFILES['ChuyenMachVon']['thong_so'] = {'so_vi_tri_ky_hieu':'7','dau_do':'Điện áp pha/điện áp dây'}
PROFILES['ChuyenMachAmpe']['thong_so'] = {'so_vi_tri_ky_hieu':'4','dau_do':'Dòng qua CT'}
PROFILES['CongTacOnOff']['thong_so'] = {'so_vi_tri_ky_hieu':'2','chuc_nang_tiep_diem':'ON/OFF'}
PROFILES['DongHoDienTuKhac']['thong_so'] = {'kieu_hien_thi':'số, lắp mặt tủ'}
PROFILES['DongHoKimNho']['thong_so'] = {'kieu_hien_thi':'kim analog'}

ID_TO_PROFILE = {id_: key for key, info in PROFILES.items() for id_ in info['cac_hinh_cad']}
assert len(ID_TO_PROFILE) == 30
assert len({r['id'] for r in ROWS if r['kind']=='view'}) == 33

def size(row):
    drawing = ezdxf.readfile(SOURCE / row['cad_dxf'])
    if drawing.header.get('$INSUNITS') != 4:
        return None
    bounds = bbox.extents(drawing.modelspace(), fast=True)
    return {'ngang': round(bounds.size.x,1), 'cao': round(bounds.size.y,1)} if bounds.has_data else None

for row in ROWS:
    key = ID_TO_PROFILE.get(row['id'])
    parent = TARGET / ('ThietBi' if key else 'TuLieuBanVe') / (key if key else row['zone'])
    role = {'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}[row['kind']]
    item = parent / role / row['id']
    item.mkdir(parents=True, exist_ok=True)
    assets = {}
    for field, name in [('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')]:
        if row.get(field):
            src = (SOURCE / row[field]).resolve()
            assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
            shutil.copy2(src, item / name)
            assets[field] = name
    data = {'id':row['id'],'thiet_bi':key,'loai_hinh':row['kind'],'ten_hinh':row['name'],'tep':assets}
    if row['kind']=='view': data['kich_thuoc_hinh_mm'] = size(row)
    (item/'thong_tin.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key, info in PROFILES.items():
    folder = TARGET / 'ThietBi' / key
    folder.mkdir(parents=True, exist_ok=True)
    info['nhom'] = 'Thiết bị đo lường hiển thị'
    (folder/'thong_tin_thiet_bi.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

expected = {r['id']: ID_TO_PROFILE.get(r['id']) for r in ROWS}
for path in TARGET.rglob('thong_tin.json'):
    data = json.loads(path.read_text(encoding='utf-8'))
    if data['id'] not in expected:
        raise ValueError(f'Unexpected record in generated folder: {path}')
    if expected[data['id']] and expected[data['id']] != path.parents[2].name:
        stale = path.parent
        assert stale.resolve().is_relative_to(TARGET.resolve())
        assert {p.name for p in stale.iterdir()}.issubset({'thong_tin.json','ban_ve.dxf','xem_truoc.svg'})
        shutil.rmtree(stale)
for folder in sorted((p for p in TARGET.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    if not any(folder.iterdir()): folder.rmdir()

print(json.dumps({'profiles':len(PROFILES),'views':len(ID_TO_PROFILE),
                  'context_views':3,'inventory_records':len(ROWS)},ensure_ascii=False))

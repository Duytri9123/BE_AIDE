"""Organize indicator, operator, fuse and contactor drawings into device profiles."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
TARGET = ROOT / 'DenBaoNutNhanCauChiContactor'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']
        if r.get('zone') in {'C03', 'A13'}]
assert len(ROWS) == 124

LS = 'https://www.ls-electric.com/ko/product/view/P01260'
CHINT = 'https://www.chintglobal.com/global/en/products/low-voltage/iec/industrial-control/nd16.html'
IDEC = 'https://www.idec.com/en-apac/switches-indicator-lights/switches-pushbuttons/22mm-25mm-30mm-switches/hw-22mm-heavy-duty'

def item(name, kind, use, place, ids, *, brand=None, code=None, spec=None, select=None, status=None, sources=None):
    return {'nhom':'Đèn báo - Nút nhấn - Cầu chì - Contactor', 'ten_kieu':name,
            'ten_san_pham':name, 'ban_chat':kind, 'cong_dung':use,
            'vi_tri_lap_dat':place, 'hang_xac_nhan':brand, 'ma_dong_san_pham':code,
            'thong_so':spec or {}, 'lua_chon_ky_thuat':select or [],
            'muc_do_xac_nhan':status or 'Chưa xác định mã đặt hàng chính xác.',
            'nguon_tham_khao':sources or [], 'cac_hinh_cad':ids}

PROFILES = {}

CONTACTOR_CANDIDATES = (
    ('MC_6a-18a_3P','MC-6a / 9a / 12a / 18a',3,'18AF','7–18','45 × 73,5'),
    ('MC_6a-18a_4P','MC-6a/4 / 9a/4 / 12a/4 / 18a/4',4,'18AF','7–18','45 × 73,5'),
    ('MC_32a-40a_3P','MC-32a / MC-40a',3,'40AF','32–40','69 × 83 (có tiếp điểm phụ bên)'),
    ('MC_50a-65a_3P','MC-50a / MC-65a',3,'65AF','50–65','79 × 106 (có tiếp điểm phụ bên)'),
    ('MC_75a-100a_3P','MC-75a / 85a / 100a',3,'100AF','75–105','94 × 140 (có tiếp điểm phụ bên)'),
    ('MC_130a-150a_3P','MC-130a / MC-150a',3,'150AF','130–150','95 × 158 (thân chính)'),
)
LS_CATALOG = 'https://www.ls-electric.com/upload/customer/download/280b6197-f4bb-4f86-a60d-917b7b8bf890/Metasol_MC_E_170915.pdf'
for n, (key, models, poles, frame, ac3, catalog_size) in enumerate(CONTACTOR_CANDIDATES,1):
    PROFILES[key]=item(f'Contactor LS {poles} cực · nhóm {models}', f'Khởi động từ {poles} cực',
        'Đóng cắt từ xa mạch động lực bằng cuộn hút điều khiển.',
        'Trong ngăn động lực của tủ điện, trước động cơ hoặc tải cần đóng cắt.',
        [f'C03_cluster3-V{n:03d}'], brand='LS Electric',
        code=models,
        spec={'so_cuc_chinh':poles,'nhom_khung':frame,
              'dong_ac3_380_440V_A':ac3,'kich_thuoc_ung_vien_mm':catalog_size},
        select=['Chọn dòng làm việc theo tải và cấp sử dụng AC-3/AC-1.',
                'Xác nhận điện áp cuộn hút, tiếp điểm phụ và phối hợp rơ le quá tải.'],
        status='Nhóm mã ứng viên theo hình dạng và tỷ lệ; dòng AC-3 là dải các biến thể trong nhóm.',
        sources=[LS_CATALOG])

PROFILES.update({
 'DeCauChi1P_KieuHop':item('Đế cầu chì 1 cực · kiểu hộp', 'Đế cầu chì lắp ray',
     'Giữ một dây chảy trong mạch điện; có thể đặt nhiều đế cạnh nhau để bảo vệ nhiều nhánh.',
     'Trên ray DIN trong ngăn bảo vệ.', ['C03_cluster4-V001'],
     spec={'so_cuc_moi_de':1,'be_rong_moi_de_mm':'khoảng 18','so_de_trong_hinh':3,
           'co_day_chay':'Chưa xác định','dong_dinh_muc_de':'Chưa xác định'},
     select=['Chọn cỡ dây chảy, dòng và điện áp danh định theo mã đế thực tế.'],
     status='Hình có ba đế một cực ghép cạnh nhau; chưa xác định hãng và mã.'),
 'DeCauChi1P_KieuGat':item('Đế cầu chì 1 cực · kiểu gạt', 'Đế cầu chì lắp ray',
     'Giữ một dây chảy trong mạch điện; các đế lắp sát nhau theo số nhánh cần bảo vệ.',
     'Trên ray DIN trong ngăn bảo vệ.', ['C03_cluster4-V002','C03_cluster4-V004'],
     spec={'so_cuc_moi_de':1,'be_rong_moi_de_mm':'khoảng 18',
           'nhan_nhin_thay_tren_hinh':'5 A trên một mô-đun; chưa xác định đây là dòng dây chảy hay dòng định mức đế',
           'co_day_chay':'Chưa xác định','dong_dinh_muc_de':'Chưa xác định'},
     select=['Chọn cỡ dây chảy, dòng và điện áp danh định theo mã đế thực tế.'],
     status='Hai hình thể hiện cùng kiểu đế một cực; lần lượt bố trí năm và ba đế. Chưa xác định hãng và mã.'),
 'CauChi_1P':item('Đế cầu chì 1 cực', 'Đế cầu chì lắp ray',
     'Bảo vệ một cực mạch điều khiển hoặc động lực bằng dây chảy.',
     'Trên ray DIN gần mạch cần bảo vệ.', ['C03_cluster4-V010'], spec={'so_cuc':1},
     select=['Chọn cỡ dây chảy, dòng, điện áp và khả năng cắt phù hợp.']),
 'NutXoay_ChonCheDo':item('Công tắc xoay chọn chế độ', 'Công tắc chọn nhiều vị trí',
     'Chọn chế độ vận hành như AUTO/MAN hoặc các trạng thái điều khiển.',
     'Gắn trên mặt cửa tủ điều khiển.',
     ['C03_cluster5-V001','C03_cluster5-V005','C03_cluster5-V009'],
     spec={'kieu_tac_dong':'xoay duy trì'},
     select=['Xác định số vị trí và sơ đồ tiếp điểm NO/NC.',
             'Chọn đường kính lỗ lắp, dòng và điện áp tiếp điểm.']),
 'NutNhan_DieuKhien':item('Nút nhấn điều khiển mặt tủ', 'Nút nhấn tác động tức thời',
     'Phát lệnh điều khiển khi người vận hành nhấn nút.',
     'Gắn trên mặt cửa tủ điều khiển.',
     ['C03_cluster5-V002','C03_cluster5-V003','C03_cluster5-V004'],
     select=['Chọn màu và ký hiệu theo chức năng START/STOP/RESET.',
             'Kiểm tra tiếp điểm NO/NC, lỗ lắp và khả năng chịu tải tiếp điểm.'],
     status='Ba hình mặt trước cùng kiểu điều khiển; chưa đọc được mã và cấu hình tiếp điểm.'),
 'DenBao_TrangThai':item('Đèn báo trạng thái mặt tủ', 'Đèn báo tín hiệu',
     'Hiển thị trạng thái hoặc cảnh báo của mạch điều khiển.',
     'Gắn trên mặt cửa tủ điện.',
     ['C03_cluster5-V006','C03_cluster5-V007'],
     select=['Chọn màu theo chức năng, điện áp cấp đèn AC/DC và đường kính lỗ lắp.'],
     status='Có hình mặt trước và mặt bên; chưa đọc được model hoặc điện áp đèn.'),
 'DenBao_Pha_57x30':item('Đèn báo pha đầu tròn · thân dài', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V002'], spec={'kich_thuoc_hinh_mm':'57 × 30'},
     select=['Xác định điện áp đèn, màu báo và lỗ lắp.']),
 'DenBao_Pha_51x28':item('Đèn báo pha đầu tròn · thân ngắn', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V003'], spec={'kich_thuoc_hinh_mm':'51 × 28'},
     select=['Xác định điện áp đèn, màu báo và lỗ lắp.']),
 'DenBao_Pha_80x41':item('Đèn báo pha thân mô-đun · cỡ tiêu chuẩn', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V004','C03_cluster6-V005'],
     spec={'kich_thuoc_hinh_mm':'80 × 41,5'},
     select=['Kiểm tra lỗ lắp, điện áp cấp và kiểu đấu nối.']),
 'DenBao_Pha_80x51':item('Đèn báo pha thân mô-đun · cỡ lớn', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V006','C03_cluster6-V007'],
     spec={'kich_thuoc_hinh_mm':'80 × 51,5'},
     select=['Kiểm tra lỗ lắp, điện áp cấp và kiểu đấu nối.']),
 'DenBao_Pha_Mong':item('Đèn báo pha đầu phẳng · thân mỏng', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V008','C03_cluster6-V009','C03_cluster6-V011'],
     select=['Xác định bề dày mặt tủ, lỗ lắp và điện áp đèn.']),
 'CHINT_DenBaoPha':item('Đèn báo pha CHINT · thân 62 mm', 'Đèn báo pha mặt tủ',
     'Hiển thị có điện áp tại một pha.', 'Gắn trên mặt cửa tủ, nối với mạch báo pha.',
     ['C03_cluster6-V010'], brand='CHINT',
     spec={'kich_thuoc_hinh_mm':'62 × 46','dong_ung_vien':'ND16-22C',
           'lo_lap_cua_dong_ung_vien_mm':'Ø22,3','dien_ap_den':'Chưa xác định','mau_den':'Chưa xác định'},
     select=['Xác nhận điện áp, màu đèn và đường kính lỗ lắp trước khi chọn mã.'],
     status='Hãng CHINT xác định; ND16-22C là dòng ứng viên theo chiều dài thân 62 mm. Chưa thấy mã trên hình.',
     sources=[CHINT,'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/indicator-light/nd16/manual/2004-ND16-Indicator%20Light%28Final%20Power%20Distribution%29-Manual.pdf']),
 'DenDo_MatTu':item('Đèn báo đỏ mặt tủ', 'Đèn báo tín hiệu',
     'Báo một trạng thái cần chú ý trên mặt tủ.', 'Gắn trên mặt cửa tủ điện.',
     ['A13_cluster19-V001'], spec={'mau_hien_thi':'đỏ'},
     select=['Chọn điện áp đèn và lỗ lắp; ý nghĩa báo đỏ theo sơ đồ tủ.'],
     status='Màu đỏ ghi trên bảng bố trí; NMC là tên hình, không phải mã sản phẩm.'),
})

SIGNAL_CHOICES = [
    {'hang':'IDEC','dong':'HW','doi_chieu':'Kiểm tra lỗ lắp và điện áp'},
    {'hang':'Schneider Electric','dong':'Harmony XB5','doi_chieu':'Kiểm tra lỗ lắp và điện áp'},
    {'hang':'CHINT','dong':'ND16','doi_chieu':'Kiểm tra lỗ lắp và điện áp'}]
for key, data in PROFILES.items():
    if key.startswith('MC_'):
        four_pole = key.endswith('_4P')
        data['phuong_an_cung_loai'] = [
            {'hang':'LS Electric','dong':'Metasol '+data['ma_dong_san_pham']},
            {'hang':'Schneider Electric','dong':'TeSys Deca LC1DT (4P, AC-1)' if four_pole else 'TeSys Deca LC1D (3P)'},
            {'hang':'CHINT','dong':'NC1 (4P)' if four_pole else 'NC1 (3P)'}]
        data['nguon_tham_khao'] += [
            'https://www.se.com/us/en/product/LC1DT406B7/contactor-tesys-deca-4p4-no-ac1-440v-40a-24v-ac-50-60-hz-coil-lugsring-terminals/' if four_pole else
            'https://www.se.com/us/en/download/document/1727189_01A50/',
            'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/industrial-control/ac-contactor/nc1/catalog/NC1-AC%20Contactor-Catalog.pdf']
        if four_pole:
            data['luu_y_tuong_thich'] = 'Các dòng 4 cực có thể dùng cấp sử dụng khác nhau; LC1DT 4P của Schneider công bố AC-1, không lấy dải AC-3 của LS để thay thế trực tiếp.'
    elif key == 'CHINT_DenBaoPha':
        data['phuong_an_cung_loai'] = []
    elif key.startswith('DenBao'):
        data['phuong_an_cung_loai'] = SIGNAL_CHOICES
        data['nguon_tham_khao'] += [IDEC,CHINT,
            'https://www.se.com/us/en/product/XB5AVB6/pilot-light-harmony-xb5-grey-plastic-blue-22mm-universal-led-plain-lens-24v-ac-dc/']
    elif key == 'NutXoay_ChonCheDo':
        data['phuong_an_cung_loai'] = [
            {'hang':'IDEC','dong':'HW selector','doi_chieu':'Kiểm tra số vị trí và tiếp điểm'},
            {'hang':'CHINT','dong':'NP2 selector','doi_chieu':'Kiểm tra số vị trí và tiếp điểm'},
            {'hang':'Schneider Electric','dong':'Harmony XB5 selector','doi_chieu':'Kiểm tra số vị trí và tiếp điểm'}]
    elif key == 'NutNhan_DieuKhien':
        data['phuong_an_cung_loai'] = [
            {'hang':'IDEC','dong':'HW pushbutton','doi_chieu':'Kiểm tra lỗ lắp và tiếp điểm'},
            {'hang':'Schneider Electric','dong':'Harmony XB5 pushbutton','doi_chieu':'Kiểm tra lỗ lắp và tiếp điểm'},
            {'hang':'CHINT','dong':'NP2 pushbutton','doi_chieu':'Kiểm tra lỗ lắp và tiếp điểm'}]
        data['nguon_tham_khao'] += [IDEC,
            'https://www.chintglobal.com/gb/en/products/low-voltage/iec/industrial-control/np2.html']
    elif key.startswith(('CauChi','DeCauChi')):
        data['phuong_an_cung_loai'] = [
            {'hang':'Schneider Electric','dong':'Acti9 STI 1P, mô-đun 18 mm'},
            {'hang':'CHINT','dong':'RT28 1P, mô-đun 18 mm'}]
        data['nguon_tham_khao'] += [
            'https://www.se.com/be/en/product/A9N15636/acti9-fusedisconnector-sti-1-pole-25-a-for-fuse-10-3-x-38-mm/',
            'https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/fuse/rt28/catalog/RT28-Fuse-Catalog.pdf']
        data['luu_y_tuong_thich'] = 'Hai dòng trên có cùng chức năng và bề rộng mô-đun; chưa xác định đế trong hình dùng dây chảy 10 × 38 mm.'
    if data.get('phuong_an_cung_loai') and not data.get('luu_y_tuong_thich'):
        data['luu_y_tuong_thich'] = 'Đối chiếu kích thước lắp và thông số điện trước khi chọn mã đặt hàng.'

ID_MAP={id_:key for key,p in PROFILES.items() for id_ in p['cac_hinh_cad']}
assert len(ID_MAP)==29

ASSEMBLIES = {
    'C03_cluster4-V001':'3 đế cầu chì 1 cực đặt cạnh nhau',
    'C03_cluster4-V002':'5 đế cầu chì 1 cực đặt cạnh nhau',
    'C03_cluster4-V004':'3 đế cầu chì 1 cực và phụ kiện chặn hai bên',
}

def dimensions(row):
    doc=ezdxf.readfile(SOURCE/row['cad_dxf'])
    if doc.header.get('$INSUNITS')!=4:return None
    ext=bbox.extents(doc.modelspace(),fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None

for row in ROWS:
    key=ID_MAP.get(row['id'])
    parent=TARGET/('ThietBi' if key else 'TuLieuBanVe')/(key if key else row['zone'])
    role={'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}[row['kind']]
    folder=parent/role/row['id'];folder.mkdir(parents=True,exist_ok=True)
    assets={}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        if row.get(field):
            src=(SOURCE/row[field]).resolve()
            assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
            shutil.copy2(src,folder/name);assets[field]=name
    info={'id':row['id'],'thiet_bi':key,'loai_hinh':row['kind'],
          'ten_hinh':row['name'],'tep':assets}
    if row['kind']=='view':info['kich_thuoc_hinh_mm']=dimensions(row)
    if row['id'] in ASSEMBLIES:info['cau_hinh_lap_ghep']=ASSEMBLIES[row['id']]
    (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,data in PROFILES.items():
    (TARGET/'ThietBi'/key/'thong_tin_thiet_bi.json').write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

expected={r['id']:ID_MAP.get(r['id']) for r in ROWS}
for path in TARGET.rglob('thong_tin.json'):
    data=json.loads(path.read_text(encoding='utf-8'))
    if data['id'] not in expected: raise ValueError(f'Unexpected record: {path}')
    if expected[data['id']] and path.parents[2].name != expected[data['id']]:
        stale=path.parent
        assert stale.resolve().is_relative_to(TARGET.resolve())
        assert {p.name for p in stale.iterdir()}.issubset({'thong_tin.json','ban_ve.dxf','xem_truoc.svg'})
        shutil.rmtree(stale)
for path in (TARGET/'ThietBi').rglob('thong_tin_thiet_bi.json'):
    if path.parent.name not in PROFILES:
        assert path.parent.resolve().is_relative_to(TARGET.resolve())
        assert {p.name for p in path.parent.rglob('*') if p.is_file()} == {'thong_tin_thiet_bi.json'}
        path.unlink()
for folder in sorted((p for p in TARGET.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
    if not any(folder.iterdir()):folder.rmdir()

print(json.dumps({'profiles':len(PROFILES),'attached_views':len(ID_MAP),
                  'context_views':sum(r['kind']=='view' for r in ROWS)-len(ID_MAP),
                  'inventory_records':len(ROWS)},ensure_ascii=False))

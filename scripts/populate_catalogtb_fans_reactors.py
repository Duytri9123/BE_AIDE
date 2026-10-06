"""Curate cooling accessories and reactor views using product-family evidence."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = [r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']
        if r.get('zone') in {'A11','A16','C01','C11'}]
assert len(ROWS) == 102

LEIPOLE = {n:f'https://leipole.pl/en/products/fkl{n}/' for n in ('6621','6622','6623','6625','6626')}
REACTOR_SOURCE = 'https://circutor.com/pdf/pdfdatasheet.php?lang=en&prod=P731200000300'

def profile(name, kind, use, place, ids, *, brand=None, code=None, spec=None,
            status=None, sources=()):
    return {'nhom':'Quạt và thông gió' if kind != 'Cuộn kháng ba pha lõi thép' else 'Cuộn kháng',
            'ten_kieu':name,'ten_san_pham':name,'ban_chat':kind,'cong_dung':use,
            'vi_tri_lap_dat':place,'hang_xac_nhan':brand,'ma_dong_san_pham':code,
            'thong_so':spec or {},'muc_do_xac_nhan':status or 'Chưa xác định mã sản phẩm.',
            'nguon_tham_khao':list(sources),'cac_hinh_cad':ids}

FAN_USE = 'Đưa không khí qua lớp lọc để làm mát khoang tủ điện.'
FILTER_USE = 'Cho không khí vào hoặc ra tủ qua tấm lọc bụi; không có động cơ.'
PLACE = 'Trên vách hoặc cửa tủ, phối hợp quạt hút và cửa gió đối diện để tạo đường thông khí.'
SIZE = {'6621':116,'6622':148.5,'6623':204}
AIR = {'6621':(72,15),'6622':(72,43),'6623':(105,71)}
PROFILES = {}
for n in ('6621','6622','6623'):
    fan_ids = {'6621':['A16_cluster1-V002','A16_cluster1-V005'],
               '6622':['A16_cluster1-V007','A16_cluster1-V010'],
               '6623':['A16_cluster1-V013','A16_cluster1-V016']}[n]
    filter_ids = {'6621':['A16_cluster1-V001','A16_cluster1-V003','A16_cluster1-V004'],
                  '6622':['A16_cluster1-V006','A16_cluster1-V008','A16_cluster1-V009','A16_cluster1-V011'],
                  '6623':['A16_cluster1-V012','A16_cluster1-V014','A16_cluster1-V015','A16_cluster1-V017']}[n]
    PROFILES[f'Leipole_FKL{n}_230'] = profile(
        f'Quạt lọc tủ Leipole FKL{n}.230', 'Quạt lọc gió tủ điện', FAN_USE, PLACE, fan_ids,
        brand='Leipole',code=f'FKL{n}.230',
        spec={'dien_ap_VAC':230,'tan_so_Hz':'50/60','kich_thuoc_mat_truoc_mm':f'{SIZE[n]} × {SIZE[n]}',
              'luu_luong_tu_do_m3_h':AIR[n][0],
              'luu_luong_voi_mot_tam_loc_m3_h':AIR[n][1]},
        status='Mã FKL và đuôi .230 ghi trên hình, kích thước mặt trước khớp dòng sản phẩm.',
        sources=[LEIPOLE[n]])
    PROFILES[f'Leipole_FKL{n}_300'] = profile(
        f'Tấm lọc gió Leipole FKL{n}.300', 'Tấm lọc thông gió thụ động', FILTER_USE, PLACE,
        filter_ids, brand='Leipole',code=f'FKL{n}.300',
        spec={'kich_thuoc_mat_truoc_mm':f'{SIZE[n]} × {SIZE[n]}','dong_co':'Không có'},
        status=('Một hình có nhãn 6621 sai nhưng rộng 204 mm và cùng hình dạng 6623; đã ghép theo kích thước.'
                if n=='6623' else 'Mã .300 trên hình và kích thước khớp tấm lọc cùng dòng.'),
        sources=[LEIPOLE[n]])

for n,front,view_id in [('6621',116.5,'C01_cluster6-V001'),('6622',148.5,'C01_cluster6-V002'),
                        ('6623',204,'C01_cluster6-V003'),('6625',255,'C01_cluster6-V004'),
                        ('6626',323,'C01_cluster6-V005')]:
    PROFILES[f'LuoiGio_{n}'] = profile(
        f'Lưới thông gió {front} mm · ứng viên FKL{n}.300', 'Lưới thông gió thụ động',
        'Che lỗ thông gió và giữ tấm lọc bụi trong tủ điện.', PLACE,[view_id],
        spec={'kich_thuoc_mat_truoc_mm':f'{front} × {front}','dong_ung_vien':f'FKL{n}.300'},
        status='Hình không ghi hãng hoặc mã. Dòng FKL được gợi ý theo hình dạng và cỡ mặt; chưa xác nhận thay thế trực tiếp.',
        sources=[LEIPOLE[n]])

PROFILES['TamCheQuat120'] = profile(
    'Tấm che quạt vuông · khoảng 120 mm','Tấm che bảo vệ quạt',
    'Che cánh quạt và giữ vật lạ khỏi cửa hút hoặc xả gió.',
    'Trên mặt ngoài cửa quạt của tủ điện.',['C01_cluster5-V001'],
    spec={'kich_thuoc_hinh_mm':'119,9 × 119,9'},
    status='Chỉ xác định hình và cỡ; chưa xác định hãng, vật liệu hoặc mã.')
PROFILES['KhungGio130'] = profile(
    'Khung lỗ gió vuông 130 mm','Khung hoặc lỗ lắp thông gió',
    'Tạo vị trí lắp lưới thông gió hoặc quạt trên vỏ tủ.',
    'Trên vách tủ điện.',['A11_cluster4-V016'],
    spec={'kich_thuoc_hinh_mm':'130 × 130'},
    status='Hình là biên dạng khung/lỗ lắp; chưa xác định đây là sản phẩm bán rời.')

PROFILES['CuonKhang3P_ChuaRoLoai'] = profile(
    'Cuộn kháng ba pha · chưa rõ ứng dụng', 'Cuộn kháng ba pha lõi thép',
    'Tạo điện kháng trong mạch ba pha; chức năng chính xác phụ thuộc vị trí đấu nối.',
    'Có thể ở đầu vào biến tần hoặc nối tiếp với cấp tụ bù; chưa xác định từ hai hình này.',
    ['C11_cluster6-V001','C11_cluster6-V002'],
    spec={'so_pha_theo_hinh':3,'dong_dinh_muc':'Chưa xác định',
          'dien_khang_mH':'Chưa xác định','tan_so_cong_huong':'Chưa xác định'},
    status='Hai hình cho thấy kết cấu lõi thép/cuộn dây ba pha. Chưa có nhãn để kết luận đây là cuộn kháng lọc sóng hài hay kháng biến tần.',
    sources=[REACTOR_SOURCE])

ID_MAP = {id_:key for key,p in PROFILES.items() for id_ in p['cac_hinh_cad']}
assert len(ID_MAP)==26

def size(row):
    doc=ezdxf.readfile(SOURCE/row['cad_dxf'])
    if doc.header.get('$INSUNITS')!=4:return None
    ext=bbox.extents(doc.modelspace(),fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None

ROLE={'view':'HinhChieu','block':'ThanhPhanCAD','group':'BanVeCum','region':'BanVeVung'}
for row in ROWS:
    category='Cuộn kháng' if row['zone']=='C11' else 'Quạt'
    key=ID_MAP.get(row['id'])
    folder=ROOT/category/('ThietBi' if key else 'TuLieuBanVe')/(key if key else row['zone'])/ROLE[row['kind']]/row['id']
    folder.mkdir(parents=True,exist_ok=True)
    assets={}
    for field,name in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        if not row.get(field):continue
        src=(SOURCE/row[field]).resolve()
        assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
        shutil.copy2(src,folder/name)
        assets[field]=name
    info={'id':row['id'],'thiet_bi':key,'loai_hinh':row['kind'],
          'ten_hinh':row['name'],'tep':assets}
    if row['kind']=='view':info['kich_thuoc_hinh_mm']=size(row)
    if row['id']=='A16_cluster1-V017':info['ghi_chu']='Nhãn 6621 sai; kích thước và hình dạng thuộc cỡ 6623.'
    (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for key,data in PROFILES.items():
    category='Cuộn kháng' if key.startswith('CuonKhang') else 'Quạt'
    (ROOT/category/'ThietBi'/key/'thong_tin_thiet_bi.json').write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(PROFILES),'attached_views':len(ID_MAP),
                  'records':len(ROWS)},ensure_ascii=False))

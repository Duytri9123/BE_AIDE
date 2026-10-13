"""Build individual cabinet accessory records from the accessory CAD inventory."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import ezdxf
from ezdxf import bbox

BASE = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB' / 'Phụ kiện tủ điện'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
ROWS = {r['id']: r for r in json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))['records']}
PROFILES = {}


def add(key, title, nature, purpose, position, ids, *, code=None, brand=None,
        spec=None, sources=(), status='Chưa xác định mã hàng cụ thể.'):
    assert key.isascii() and key not in PROFILES
    assert all(i in ROWS and ROWS[i]['kind'] == 'view' for i in ids)
    PROFILES[key] = {
        'nhom': 'Phụ kiện tủ điện', 'ten_kieu': title, 'ten_san_pham': title,
        'ban_chat': nature, 'cong_dung': purpose, 'vi_tri_lap_dat': position,
        'hang_xac_nhan': brand, 'ma_dong_san_pham': code,
        'thong_so': spec or {}, 'muc_do_xac_nhan': status,
        'nguon_tham_khao': list(sources), 'cac_hinh_cad': ids,
    }


def views(zone, cluster, numbers):
    return [f'{zone}_cluster{cluster}-V{n:03d}' for n in numbers]


lock_use = 'Giữ cửa tủ ở trạng thái đóng và cho phép mở khi thao tác bảo trì.'
lock_place = 'Lắp trên cánh cửa, làm việc với ngàm hoặc phần đối diện trên khung tủ.'
for cluster, family, model in [
    (8,'Khóa bấm cỡ lớn',None),(9,'Khóa bấm cỡ trung','AB301-3-1'),
    (10,'Khóa bấm cỡ nhỏ','AB301-2-1'),(11,'Khóa bấm kiểu 4','A47036'),
    (12,'Khóa bấm kiểu 3','MS463-1-1A'),(13,'Khóa bấm kiểu 2',None),
    (14,'Khóa bấm kiểu 1','MS603-3'),(16,'Khóa tay xoay kiểu 4','MS306-1'),
    (17,'Khóa tay xoay kiểu 3','A2055'),(18,'Khóa tay xoay kiểu 2','A45'),
    (19,'Khóa tay xoay kiểu 1','A19'),(20,'Khóa chìa hai ngạnh','MS705-1'),
    (21,'Khóa chìa tam giác','MS8712')]:
    code = f' · nhãn {model}' if model else ''
    add(f'KhoaTu_{cluster:02d}',family+code,'Khóa cửa tủ điện',lock_use,lock_place,
        views('A06',cluster,[1,2]),spec={'ma_tren_ban_ve':model} if model else {},
        status='Mã ghi trên bản vẽ; chưa đối chiếu được với mã đặt hàng của hãng.' if model else 'Chưa xác định hãng và mã hàng.')
add('KhoaBamRoi','Khóa bấm rời','Khóa cửa tủ điện',lock_use,lock_place,views('A06',15,[1]))
add('VitVanCuaTu','Vít vặn cửa tủ','Chốt vặn cửa tủ',lock_use,lock_place,views('A06',7,[1]))

hinge_use = 'Tạo trục quay cho cánh cửa tủ và giữ cửa trên khung.'
hinge_place = 'Giữa cánh cửa và khung tủ; chọn đúng chiều mở, chiều dày tôn và vị trí lỗ bắt.'
for cluster, label, nums in [
    (5,'Bản lề cửa kiểu BL2',[1,2]),(6,'Bản lề cửa kiểu BL1',[1,2])]:
    add(f'BanLeA06_{cluster}',label,'Bản lề cửa tủ',hinge_use,hinge_place,views('A06',cluster,nums))
for cluster, label, nums in [
    (8,'Bản lề BL1',[1,2]),(9,'Bản lề HL009',[1,2,3,4,5,6,7]),
    (10,'Bản lề lá',[1,2,3,4,5]),(11,'Bản lề rùa HL035-1',[1,2,3,4]),
    (12,'Bản lề HL012',[1,2,3,4,5]),(13,'Bản lề chốt nhỏ HL003-2',[1,2]),
    (14,'Bản lề âm HL036',[3,4,5]),(15,'Bản lề âm chốt nhỏ HL011-2',[1,2]),
    (16,'Bản lề âm chốt lớn HL011-1',[1,2]),
    (17,'Bản lề rùa HL044-1.3',[1,2])]:
    add(f'BanLeA07_{cluster}',label,'Bản lề cửa tủ',hinge_use,hinge_place,
        views('A07',cluster,nums),spec={'ma_tren_ban_ve':label.split()[-1]} if cluster not in (8,10) else {},
        status='Kiểu và mã trên bản vẽ; chưa xác định hãng hoặc biến thể đặt hàng.')

add('TaiCauM10','Móc cẩu tủ M10','Điểm nâng tủ',
    'Tạo điểm bắt dây cẩu để nâng, di chuyển vỏ tủ theo thiết kế.',
    'Trên đỉnh tủ, tại vị trí gia cường chịu lực.',views('B02',1,[1]),
    spec={'co_ren_theo_nhan':'M10'},
    status='Cỡ ren theo nhãn; tải trọng cho phép chưa xác định.',
    sources=['https://www.rittal.com/imf/none/3_6148/5505110________EN'])
add('TaiTreoTu','Tai treo tủ','Bản mã treo tủ',
    'Tạo điểm liên kết vỏ tủ với kết cấu đỡ.',
    'Ở mặt sau hoặc phía trên vỏ tủ, theo kết cấu chịu lực.',views('B02',1,[2,6]),
    status='Chưa xác định chiều dày vật liệu và tải trọng cho phép.')
add('TaiCauThep','Tai cẩu dạng bản mã','Bản mã nâng tủ',
    'Liên kết thiết bị nâng với vỏ tủ khi vận chuyển.',
    'Phía trên vỏ tủ, ở vị trí đã được gia cường.',views('B02',1,[3,4,5]),
    status='Các hình là các mặt chiếu; chưa xác định tải trọng nâng.')
add('DaiOcM8','Đai ốc M8','Chi tiết liên kết cơ khí',
    'Siết liên kết ren M8 trên bản mã hoặc khung tủ.',
    'Tại điểm bắt bu lông M8.',views('B02',1,[7,10]),
    spec={'co_ren_theo_nhan':'M8'},status='Cỡ ren theo nhãn; cấp bền chưa xác định.')
add('BuLongM8','Bu lông M8','Chi tiết liên kết cơ khí',
    'Liên kết bản mã và các chi tiết của vỏ tủ.',
    'Tại các lỗ bắt trên khung hoặc bản mã.',views('B02',1,[8,11]),
    spec={'co_ren_theo_nhan':'M8'},status='Cỡ ren theo nhãn; cấp bền và chiều dài chưa xác định.')
add('DaiOcVanM8','Đai ốc M8 có vành','Chi tiết liên kết cơ khí',
    'Siết liên kết ren M8 tại vị trí cần mặt tựa rộng.',
    'Tại điểm bắt bu lông M8.',views('B02',1,[9,12]),
    spec={'co_ren_theo_nhan':'M8'},status='Tên kiểu theo nhãn; cấp bền chưa xác định.')
add('BuLongM6','Bu lông M6','Chi tiết liên kết cơ khí',
    'Bắt các chi tiết nhỏ lên vỏ hoặc khung tủ.',
    'Tại vị trí lỗ bắt phù hợp.',views('B02',1,[13]),spec={'co_ren_theo_nhan':'M6'})

for key,title,ids in [
    ('SuDoThanhCai_Taiwan','Đế sứ đỡ thanh cái 80 × 50 mm',[1]),
    ('ThanhDoCachDien_295x35','Thanh đỡ cách điện 295 × 35 mm',[2]),
    ('ChiTietDo_30x35','Chi tiết đỡ cách điện 30 × 35 mm',[3,4]),
    ('ThanhDoCachDien_130x35','Thanh đỡ cách điện 130 × 35 mm',[5,6]),
    ('SuDoThanhCai_40x138','Cặp sứ đỡ thanh cái 40 × 138,5 mm',[7,8])]:
    add(key,title,'Giá đỡ cách điện',
        'Đỡ thanh dẫn điện và cách điện với khung tủ.',
        'Trong khoang thanh cái, bắt trên khung đỡ.',views('B05',1,ids),
        status='Đã tách theo hình và cỡ. Chưa xác định vật liệu, điện áp chịu đựng và tải cơ của đúng biến thể.')
add('KepThanhDong','Kẹp thanh đồng','Kẹp giữ thanh dẫn',
    'Giữ thanh đồng cố định trên bộ đỡ.',
    'Trên cụm sứ đỡ hoặc giá đỡ thanh cái.',views('B05',1,[9,10]),
    status='Chưa xác định tiết diện thanh dẫn tương thích.')
add('KhayTaiLieu','Khay tài liệu gắn cửa tủ','Túi đựng sơ đồ',
    'Giữ bản vẽ và hướng dẫn vận hành bên trong tủ.',
    'Mặt trong cánh cửa tủ.',views('B06',1,[1]),
    sources=['https://www.rittal.com/pdf-creator/variant/de-de/4116000'])

add('MangDayNhua','Máng đi dây nhựa','Máng dây trong tủ',
    'Dẫn và sắp xếp dây điều khiển, cho phép mở nắp để bảo trì.',
    'Trên tấm lắp thiết bị hoặc thanh đỡ trong tủ.',views('C02',2,[1]),
    status='Chưa xác định bề rộng, chiều cao và kiểu rãnh của đoạn máng.')
add('NhanCanhBao','Nhãn cảnh báo điện','Nhãn an toàn',
    'Cảnh báo nguy cơ điện và xác định khu vực cần thận trọng.',
    'Trên cửa hoặc tấm che gần bộ phận mang điện.',views('C02',3,[1,2,3]))
for key,title,ids in [
    ('SuKepThanhCai_C100','Sứ kẹp thanh cái C100 · 100 mm',[2,3,4,12]),
    ('SuKepThanhCai_EL','Bộ kẹp thanh cái EL · 100 mm',[5,6,7,8]),
    ('SuKepThanhCai_100','Giá kẹp thanh cái · 100,5 mm',[9]),
    ('SuKepThanhCai_300','Thanh kẹp cách điện · 300,1 mm',[10]),
    ('SuKepThanhCai_400','Thanh kẹp cách điện · 400 mm',[11])]:
    add(key,title,'Bộ đỡ cách điện',
        'Giữ thanh cái và duy trì khoảng cách cách điện giữa thanh cái với kết cấu tủ.',
        'Trong khoang phân phối thanh cái.',views('C02',4,ids),
        status='Đã tách theo cỡ và kiểu hình. Chưa xác định dòng, điện áp và lực ngắn mạch cho phép.',
        sources=['https://www.rittal.com/us-en_US/products/PG20231215POW101/PG20240417STR001/PG20241204STR001/PG20241210STR002/PRO42036?variantId=9677600'])
add('CuaSoCongTo','Cửa sổ quan sát công tơ','Cửa sổ quan sát',
    'Cho phép đọc chỉ số mà không cần mở cửa tủ.',
    'Trên cánh cửa tủ, đối diện vị trí công tơ.',views('C02',5,[1]))
add('NhanCaiTu','Nhãn cài thiết bị','Giá giữ nhãn',
    'Hiển thị tên lộ hoặc tên thiết bị để nhận biết khi vận hành.',
    'Trên mặt tủ hoặc gần thiết bị được đánh dấu.',views('C02',6,[1,2,3,4]))

for number in (70,120,185,240,300,400):
    ix=(70,120,185,240,300,400).index(number)+1
    add(f'CosDong_{number}_2',f'Đầu cos đồng · ký hiệu {number}-2',
        'Đầu cốt cáp bắt bu lông',
        'Ép vào đầu dây cáp và tạo điểm nối bằng bu lông với thanh dẫn hoặc cực thiết bị.',
        'Tại đầu cáp lực trong khoang đấu nối.',views('C07',4,[ix]),
        spec={'ky_hieu_tren_hinh':f'{number}-2'},
        status='Ký hiệu trên hình chưa đủ để xác định tiết diện cáp, số lỗ bắt và mã đặt hàng.')
add('CauNPE','Cầu đấu trung tính và tiếp địa','Thanh phân phối N và PE',
    'Tập trung các đầu dây trung tính và dây bảo vệ theo từng thanh riêng.',
    'Trong khoang đấu nối, trên giá cách điện hoặc khung tiếp địa phù hợp.',
    views('C07',5,[1,2]),status='Chưa xác định số vị trí đấu, tiết diện dây và dòng chịu tải.')

used = {i for p in PROFILES.values() for i in p['cac_hinh_cad']}
assert len(used) == sum(len(p['cac_hinh_cad']) for p in PROFILES.values())


def drawing_size(row):
    doc=ezdxf.readfile(SOURCE / row['cad_dxf'])
    if doc.header.get('$INSUNITS') != 4:
        return None
    ext=bbox.extents(doc.modelspace(),fast=True)
    return {'ngang':round(ext.size.x,1),'cao':round(ext.size.y,1)} if ext.has_data else None


for key, data in PROFILES.items():
    target=BASE/'ThietBi'/key
    for id_ in data['cac_hinh_cad']:
        row=ROWS[id_]
        folder=target/'HinhChieu'/id_
        folder.mkdir(parents=True,exist_ok=True)
        assets={}
        for field,filename in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
            src=(SOURCE/row[field]).resolve()
            assert src.is_relative_to(SOURCE.resolve()) and src.is_file()
            shutil.copy2(src,folder/filename)
            assets[field]=filename
        info={'id':id_,'thiet_bi':key,'loai_hinh':'view','ten_hinh':row['name'],
              'kich_thuoc_hinh_mm':drawing_size(row),'tep':assets}
        (folder/'thong_tin.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (target/'thong_tin_thiet_bi.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for name in ('BoLienKetM8','SuDoThanhCai','SuKepThanhCai'):
    stale=BASE/'ThietBi'/name
    if stale.exists():
        assert stale.resolve().is_relative_to((BASE/'ThietBi').resolve())
        assert {p.name for p in stale.rglob('*') if p.is_file()} <= {
            'thong_tin_thiet_bi.json','thong_tin.json','ban_ve.dxf','xem_truoc.svg','thong_tin_cad_chen.json'}
        shutil.rmtree(stale)

print(json.dumps({'profiles':len(PROFILES),'attached_views':len(used)},ensure_ascii=False))

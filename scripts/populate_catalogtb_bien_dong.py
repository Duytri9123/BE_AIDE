"""Organize linked current-transformer CAD views by maker and device family."""
import json
import re
import shutil
import unicodedata
from collections import Counter
from pathlib import Path
import ezdxf
from ezdxf import bbox

BASE = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
TARGET = BASE / 'BienDong'
SOURCE = Path(__file__).resolve().parents[2] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
inventory = json.loads((SOURCE / 'full_accessory_cad_inventory.json').read_text(encoding='utf-8'))
records = [r for r in inventory['records'] if r.get('zone') in {'A02', 'C08', 'C12'}]
assert len(records) == 218

EMIC_MODELS = {f'C08_cluster10-V{i:03d}': f'EM4H{i+2:02d}' for i in range(1, 6)}
MODEL_PREFIX = re.compile(r'^(CML\d+A|KDE \d+A|MSQ-\d+|RCT\d+|BD1200A|BD01-\d+)', re.I)

# Product-family facts are intentionally separate from drawing measurements.
# The ranges below describe available variants, never a confirmed order code.
EMIC_RANGES = {
    'EM4H03': ('200–250 A', '38 mm', '5 VA'),
    'EM4H04': ('300–600 A', '50 mm', '5–15 VA'),
    'EM4H05': ('400–1200 A', '80 mm', '5–15 VA'),
    'EM4H06': ('1500–2500 A', '110 mm', '5–15 VA'),
    'EM4H07': ('3000–5000 A', '125 mm', '5–15 VA'),
}
MIKRO_BORE = {'ZCT_40S': 40, 'ZCT_80S': 80, 'ZCT120': 120}
RCT_BORE = {'RCT35': 35, 'RCT60': 60, 'RCT90': 90, 'RCT110': 110}
LIGHTSTAR_MODELS = {
    **{f'C08_cluster5-V{i:03d}': model for i, model in enumerate(
        ('KBF-03', 'KBF-13', 'KBF-23', 'KBF-43', 'KBF-63') * 2, 1)},
    **{f'C08_cluster6-V{i:03d}': model for i, model in enumerate(
        ('KBD-13', 'KBD-23', 'KBD-43'), 1)},
}
# RCT-58 outline is approximately 108 x 121 x 57 mm in the WIZARD RCT
# product catalogue; these three views measure 106.5 x 120 x 56 mm.
# This is a frame/ratio match, not proof of the maker or ordering variant.
CML500_VIEWS = {f'C08_cluster9-V{i:03d}' for i in (3, 4, 5)}

def option(primary, secondary, aperture, accuracy, burden):
    def numbers(value):
        return [float(x.replace(',', '.')) for x in re.findall(r'\d+(?:,\d+)?', value or '')]
    currents = numbers(primary)
    secondary_values = numbers(secondary)
    aperture_values = numbers(aperture)
    aperture_shape = 'tron' if aperture and aperture.startswith('Ø') else 'chu_nhat' if len(aperture_values) == 2 else None
    return {'so_cap_A': primary, 'thu_cap_A': secondary,
            'lo_xuyen_mm': aperture, 'cap_chinh_xac': accuracy, 'tai_VA': burden,
            'so_cap_tu_A': currents[0] if currents else None,
            'so_cap_den_A': currents[-1] if currents else None,
            'thu_cap_tuy_chon_A': secondary_values,
            'lo_xuyen': ({'dang': aperture_shape,
                           'duong_kinh_mm': aperture_values[0]} if aperture_shape == 'tron' else
                          {'dang': aperture_shape, 'ngang_mm': aperture_values[0],
                           'cao_mm': aperture_values[1]} if aperture_shape == 'chu_nhat' else None),
            'cap_chinh_xac_tuy_chon': numbers(accuracy),
            'tai_tuy_chon_VA': numbers(burden)}

SELECTION_OPTIONS = {
    'EM4H03': [option('200–250', '1 hoặc 5', 'Ø38', '0,5 hoặc 1', '5')],
    'EM4H04': [option('300', '1 hoặc 5', 'Ø50', '0,5 hoặc 1', '5 hoặc 10'),
                option('400–600', '1 hoặc 5', 'Ø50', '0,5 hoặc 1', '5, 10 hoặc 15')],
    'EM4H05': [option('400–600', '1 hoặc 5', 'Ø80', '0,5 hoặc 1', '5 hoặc 10'),
                option('800–1200', '1 hoặc 5', 'Ø80', '0,5 hoặc 1', '5, 10 hoặc 15')],
    'EM4H06': [option('1500–2500', '1 hoặc 5', 'Ø110', '0,5 hoặc 1', '5, 10 hoặc 15')],
    'EM4H07': [option('3000–5000', '1 hoặc 5', 'Ø125', '0,5 hoặc 1', '5, 10 hoặc 15')],
    'KBF-03': [option('50–100', '1 hoặc 5', '7 × 16', '3', '2,5'),
               option('120', '1 hoặc 5', '7 × 16', '3', '5'),
               option('150–200', '1 hoặc 5', '7 × 16', '1', '5')],
    'KBF-13': [option('50–100', '1 hoặc 5', '7 × 16', '3', '2,5'),
               option('120', '1 hoặc 5', '7 × 16', '3', '5'),
               option('150–200', '1 hoặc 5', '7 × 16', '1', '5')],
    'KBF-23': [option('75–120', '1 hoặc 5', '10 × 21', '3', '2,5'),
               option('150', '1 hoặc 5', '10 × 21', '3', '5'),
               option('200–300', '1 hoặc 5', '10 × 21', '1', '5')],
    'KBF-43': [option('100–120', '1 hoặc 5', '20 × 30', '3', '2,5'),
               option('150', '1 hoặc 5', '20 × 30', '3', '5'),
               option('200–500', '1 hoặc 5', '20 × 30', '1', '5')],
    'KBF-63': [option('300', '1 hoặc 5', '25 × 46', '1', '5'),
               option('400–1200', '1 hoặc 5', '25 × 46', '1', '15')],
    'KBD-13': [option('50–100', '1 hoặc 5', 'Ø14', '3', '2,5'),
               option('120', '1 hoặc 5', 'Ø14', '3', '5'),
               option('150–200', '1 hoặc 5', 'Ø14', '1', '5')],
    'KBD-23': [option('50–60', '1 hoặc 5', 'Ø21,5', '3', '2,5'),
               option('75', '1 hoặc 5', 'Ø21,5', '3', '5'),
               option('100–300', '1 hoặc 5', 'Ø21,5', '1', '5')],
    'KBD-43': [option('100–120', '1 hoặc 5', 'Ø27', '3', '5'),
               option('150–300', '1 hoặc 5', 'Ø27', '1', '5'),
               option('400–500', '1 hoặc 5', 'Ø27', '1', '15')],
    'BD01': [option('150', '5', 'Ø34', '0,5', '5 hoặc 10'),
             option('300–600', '5', 'Ø50', '0,5', '10 hoặc 15')],
    'RCT-58_500-5A': [option('500', '5', 'Ø58', None, None)],
}

def enrich(analysis, model, brand, rows):
    """Add use and configuration facts without inventing an exact CAD SKU."""
    detail = []
    if model in EMIC_RANGES:
        primary, bore, burden = EMIC_RANGES[model]
        analysis['ban_chat'] = 'Biến dòng đo lường dạng xuyến, một tỷ số'
        analysis['cong_dung'] = 'Hạ dòng điện xoay chiều của một pha xuống mức phù hợp cho công tơ, ampe kế hoặc bộ giám sát.'
        analysis['vi_tri_lap_dat'] = 'Lắp quanh một dây pha hoặc thanh cái trong ngăn đo lường của tủ điện; đấu đầu thứ cấp S1–S2 đến thiết bị đo.'
        detail = [f'Dòng sơ cấp của dòng {model}: {primary}', 'Thứ cấp tùy chọn: 1 A hoặc 5 A',
                  f'Lỗ xuyên dây/thanh cái: Ø{bore}', f'Công suất theo biến thể: {burden}',
                  'Cấp chính xác theo biến thể: 0,5 hoặc 1']
    elif model == 'EM4H09D':
        analysis['ban_chat'] = 'Biến dòng dạng xuyến EMIC'
        analysis['cong_dung'] = 'Tạo tín hiệu dòng thứ cấp phục vụ đo lường hoặc giám sát dòng tải.'
        detail = ['Chưa xác định được tỷ số, tải VA và cấp chính xác của đúng biến thể EM4H09D.']
    elif model.startswith('ZCT'):
        analysis['ban_chat'] = 'Biến dòng thứ tự không (ZCT)'
        analysis['cong_dung'] = 'Đo tổng dòng dư để phát hiện rò điện/chạm đất; tín hiệu đưa tới rơ le bảo vệ, không dùng như CT đo dòng tải từng pha.'
        analysis['vi_tri_lap_dat'] = 'Bao quanh đồng thời các dây pha và dây trung tính nếu có tại lộ cần bảo vệ; dây PE đi ngoài lõi.'
        if model in MIKRO_BORE:
            detail = [f'Đường kính lỗ luồn dây của dòng {model.replace("_", "")}: {MIKRO_BORE[model]} mm',
                      'Dùng kèm rơ le giám sát dòng rò tương thích.']
        else:
            detail = ['Ký hiệu 300A chưa đủ để suy ra tỷ số 300/5 A hoặc ngưỡng tác động của bộ bảo vệ.']
    elif model == 'BD01':
        analysis['ban_chat'] = 'Biến dòng đo lường hạ thế kiểu BD01, lõi xuyến tròn'
        analysis['cong_dung'] = 'Biến đổi dòng xoay chiều của một pha để cấp cho đồng hồ đo hoặc công tơ.'
        analysis['vi_tri_lap_dat'] = 'Lắp quanh một cáp hoặc thanh dẫn tại ngăn đo lường hạ thế; chọn lỗ xuyên phù hợp tiết diện dây.'
        detail = ['Họ BD01 có các biến thể sơ cấp từ 50 A tới nhiều nghìn ampe.',
                  'Cấp chính xác 0,5 đối với dòng đo lường trong danh mục BD01.',
                  'Tỷ số và công suất VA của từng hình cần khớp biến thể trước khi sử dụng.']
    elif model == 'RCT-58_500-5A':
        analysis['ban_chat'] = 'Biến dòng đo lường xuyến tròn RCT-58'
        analysis['cong_dung'] = 'Biến đổi dòng điện một pha 500 A thành tín hiệu 5 A cho ampe kế, công tơ hoặc bộ giám sát.'
        analysis['vi_tri_lap_dat'] = 'Lắp bao quanh một dây pha hoặc thanh dẫn tại lộ cần đo trong tủ điện hạ thế.'
        analysis['thong_so']['dong_so_cap_dinh_muc_A'] = 500
        analysis['thong_so']['dong_thu_cap_dinh_muc_A'] = 5
        analysis['thong_so']['ty_so'] = '500/5 A'
        analysis['ma_dong_san_pham'] = 'RCT-58'
        analysis['ten_san_pham'] = 'RCT-58 500/5 A · Biến dòng đo lường xuyến tròn'
        analysis['muc_do_xac_nhan'] = 'Khớp hình và kích thước; chưa đối chiếu nhãn trên thiết bị'
        detail = ['Lỗ luồn dây danh nghĩa: Ø58 mm.',
                  'Chưa xác định cấp chính xác và công suất VA của đúng biến thể.']
    elif model in RCT_BORE:
        analysis['ban_chat'] = 'Biến dòng đo lường dạng tròn RCT'
        analysis['cong_dung'] = 'Lấy mẫu dòng điện của một pha để cấp cho đồng hồ đo hoặc bộ giám sát tải.'
        analysis['vi_tri_lap_dat'] = 'Luồn một dây pha hoặc thanh cái qua lỗ biến dòng tại lộ cần đo trong tủ điện.'
        detail = [f'Cỡ lỗ danh nghĩa của dòng RCT: Ø{RCT_BORE[model]} mm',
                  'Tỷ số, công suất và cấp chính xác thay đổi theo biến thể đặt hàng.']
    elif model.startswith('MSQ-'):
        analysis['ban_chat'] = 'Biến dòng đo lường dạng cửa sổ vuông MSQ'
        analysis['cong_dung'] = 'Lấy tín hiệu dòng xoay chiều của một pha để đo dòng, điện năng hoặc giám sát phụ tải.'
        analysis['vi_tri_lap_dat'] = 'Ôm quanh một thanh cái hoặc dây pha trong ngăn đo lường; cỡ cửa sổ tăng theo số trong tên dòng MSQ.'
        detail = ['Số trong tên dòng là cỡ khung/cửa sổ của họ MSQ, không phải tỷ số biến dòng.',
                  'Tỷ số 1/5 A, tải VA và cấp chính xác cần chọn theo đúng mã đặt hàng.']
    elif model.startswith(('KBF-', 'KBD-')):
        is_window = model.startswith('KBF-')
        analysis['ban_chat'] = ('Biến dòng ba pha ba cửa sổ chữ nhật' if is_window else
                                'Biến dòng ba pha ba cửa sổ tròn')
        analysis['cong_dung'] = 'Tạo ba tín hiệu dòng độc lập cho đo lường hoặc giám sát các pha của một lộ điện.'
        analysis['vi_tri_lap_dat'] = 'Lắp tại bộ thanh cái hoặc dây dẫn ba pha trong tủ điện; mỗi pha đi qua một cửa sổ tương ứng.'
        openings = {'KBF-03':'7 × 16 mm','KBF-13':'7 × 16 mm','KBF-23':'10 × 21 mm',
                    'KBF-43':'20 × 30 mm','KBF-63':'25 × 46 mm',
                    'KBD-13':'Ø14 mm','KBD-23':'Ø21,5 mm','KBD-43':'Ø27 mm'}
        detail = ['Ba cửa sổ luồn dây cho mạch ba pha bốn dây (3P4W).',
                  f'Cỡ cửa sổ của dòng {model}: {openings[model]}',
                  'Thứ cấp có tùy chọn 1 A hoặc 5 A; tỷ số và tải VA theo biến thể.']
    elif model.startswith('CML'):
        analysis['ban_chat'] = 'Biến dòng đo lường dạng cửa sổ CML'
        analysis['cong_dung'] = 'Biến đổi dòng của một lộ pha thành dòng thứ cấp cho hệ đo lường hoặc giám sát.'
        detail = ['Mã CML thể hiện một dòng/cỡ thiết bị; dòng và tỷ số cụ thể cần xác nhận theo nhãn từng biến thể.']
    elif model.startswith('KDE-'):
        analysis['ban_chat'] = 'Biến dòng đo lường dạng xuyên tâm'
        analysis['cong_dung'] = 'Cấp tín hiệu dòng cho thiết bị đo và giám sát tải của lộ điện.'
        detail = ['Giá trị A trong tên nhóm chưa đủ xác nhận tỷ số thứ cấp hoặc cấp chính xác.']
    elif model.startswith('PCT'):
        analysis['ban_chat'] = 'Biến dòng dùng cho mạch bảo vệ PCT'
        analysis['cong_dung'] = 'Cấp tín hiệu dòng cho rơ le bảo vệ quá dòng hoặc sự cố của lộ điện.'
        detail = ['Tỷ số ghi trong tên nhóm được lưu riêng; cấp bảo vệ và tải VA chưa xác định.']
    elif model == 'BienDongVuong_600A':
        analysis['ban_chat'] = 'Biến dòng đo lường dạng cửa sổ vuông'
        analysis['cong_dung'] = 'Lấy tín hiệu dòng tải cho đồng hồ đo hoặc bộ giám sát.'
        analysis['vi_tri_lap_dat'] = 'Lắp quanh một thanh cái trong tủ điện hạ thế.'
        detail = ['600 A là giá trị ghi cùng bộ hình; mã sản phẩm và tỷ số thứ cấp chưa được xác định.']
    elif model.startswith('CT') or model.startswith('BD'):
        analysis['ban_chat'] = 'Biến dòng đo lường'
        analysis['cong_dung'] = 'Cấp tín hiệu dòng tỷ lệ với dòng tải cho đồng hồ đo, công tơ hoặc bộ giám sát.'
        detail = ['Tỷ số chỉ được xem là xác định khi tên thiết bị ghi rõ cả sơ cấp và thứ cấp.']
    else:
        analysis['ban_chat'] = 'Cụm hình biến dòng cần phân loại thêm'
        analysis['cong_dung'] = 'Các hình trong hồ sơ cùng mô tả bộ phận hoặc các biến thể liên quan của biến dòng.'
        detail = ['Chưa đủ mã sản phẩm để xác định một cấu hình điện duy nhất.']
    analysis['dac_diem'] = detail
    analysis['phan_loai_chon'] = {
        'muc_dich': ('bao_ve_dong_ro' if model.startswith('ZCT') else
                     'bao_ve_qua_dong' if model.startswith('PCT') else 'do_luong'),
        'so_pha': 3 if model.startswith(('KBF-', 'KBD-')) else 1 if not model.startswith('ZCT') else None,
        'so_CT_trong_cum': 3 if model.startswith(('KBF-', 'KBD-')) else 1,
        'mach_phu_hop': '3P4W' if model.startswith(('KBF-', 'KBD-')) else None,
    }
    if model != 'RCT-58_500-5A':
        analysis['ten_san_pham'] = f"{model} · {analysis['ban_chat']}" if model != 'BienDongVuong_600A' else 'Biến dòng vuông 600 A'
    confirmed_family = (model == 'RCT-58_500-5A' or model in EMIC_RANGES or model in MIKRO_BORE or
                        model.startswith(('KBF-', 'KBD-', 'MSQ-', 'RCT')) or model == 'BD01')
    if model != 'RCT-58_500-5A':
        analysis['ma_dong_san_pham'] = model.replace('_', '') if confirmed_family else None
    analysis['lua_chon_ky_thuat'] = SELECTION_OPTIONS.get(model, [])
    analysis['trang_thai_lua_chon'] = ('Dải cấu hình của dòng sản phẩm; cần chọn đúng biến thể'
                                      if analysis['lua_chon_ky_thuat'] else 'Chưa đủ thông số chọn thiết bị')
    if model in MIKRO_BORE:
        analysis['lua_chon_ky_thuat'] = [option(None, None, f'Ø{MIKRO_BORE[model]}', None, None)]
        analysis['trang_thai_lua_chon'] = 'ZCT: chọn theo lỗ luồn dây và rơ le dòng rò tương thích'
    elif model in RCT_BORE:
        analysis['lua_chon_ky_thuat'] = [option(None, None, f'Ø{RCT_BORE[model]}', None, None)]
        analysis['trang_thai_lua_chon'] = 'Chỉ xác định cỡ lỗ; tỷ số và tải phải chọn theo biến thể'
    if model == 'RCT90':
        analysis['dac_diem'] = [
            'RCT-90 là cỡ biến dòng vòng có lỗ xuyên danh nghĩa Ø90 mm.',
            'Một dòng RCT-90 được công bố với các tỷ số 800/5–2000/5 A, cấp 1 và tải 15 VA; đây là dải của nhà sản xuất, chưa phải cấu hình của hình này.',
        ]
        analysis['lua_chon_ky_thuat'] = [option('800–2000', '5', 'Ø90', '1', '15')]
        analysis['trang_thai_lua_chon'] = 'Dải tham khảo Nitech RCT-90; chưa xác định hãng và tỷ số của thiết bị trong hình.'
        analysis['muc_do_xac_nhan'] = 'Nhãn vùng ghi RCT90; hai hình là mặt đỉnh và mặt cạnh. Hãng, tỷ số và VA của đúng thiết bị chưa xác định.'
        analysis['nguon_tham_khao'] = ['https://www.nitech-asia.com/RCT.html']
    return analysis

def cad_size(row):
    drawing = ezdxf.readfile(SOURCE / row['cad_dxf'])
    if drawing.header.get('$INSUNITS') != 4:
        return None
    bounds = bbox.extents(drawing.modelspace(), fast=True)
    if not bounds.has_data:
        return None
    return {'ngang': round(bounds.size.x, 1), 'cao': round(bounds.size.y, 1)}

def classify(row):
    code, name, zone, kind = row['id'], row['name'], row['zone'], row['kind']
    if kind == 'region':
        return None, f'BanVeTongHop_{zone}', 'drawing_context'
    if kind == 'group':
        return None, f'CumTongHop_{zone}', 'drawing_context'
    if code in LIGHTSTAR_MODELS:
        return 'LightStar', f'BienDongBaPha/{LIGHTSTAR_MODELS[code]}', 'mã đối chiếu theo hình dạng và kích thước sản phẩm'
    if code in CML500_VIEWS:
        return None, 'RCT-58_500-5A', 'khớp hình dạng và kích thước dòng RCT-58'
    if code.startswith('C08_cluster9-V0') and name.startswith('*U'):
        return None, 'C08_HinhBoSung_CML', 'drawing_context'
    if code in EMIC_MODELS:
        return 'EMIC', EMIC_MODELS[code], 'hình thiết bị; ghép mã theo thứ tự/kích thước trên ảnh'
    if code.startswith('C08_cluster10') or row.get('brand') == 'EMIC':
        return None, 'C08_HinhBoSung_EM4H', 'drawing_context'
    if kind == 'block':
        return None, f'{zone}_HinhBoSung', 'drawing_context'
    if zone == 'A02':
        if code.startswith('A02_abb'):
            return 'ABB', 'ZCT-300A', 'các hình trong cùng cụm CAD'
        if 'MIKRO' in row['group']:
            return 'MIKRO', row['group'].replace('MIKRO ', ''), 'các hình trong cùng cụm CAD'
        if row['group'].startswith('CT-600A-VUONG'):
            return None, 'BienDongVuong_600A', 'các hình trong cùng hàng CAD'
        ratio_name = re.fullmatch(r'(P?CT)\s+(\d+)/(\d+)\s*A', row['group'], re.I)
        if ratio_name:
            return None, f'{ratio_name.group(1).upper()}_{ratio_name.group(2)}-{ratio_name.group(3)}A', 'các hình trong cùng hàng CAD'
        return None, row['group'], 'các hình trong cùng hàng CAD'
    if zone == 'C08':
        match = re.match(r'C08_cluster(\d+)', code)
        n = match.group(1) if match else None
        brand = {'2':'MIKRO','4':'MITEX','5':'LightStar','6':'LightStar',
                 '7':'MORELE','8':'MORELE'}.get(n)
        model = MODEL_PREFIX.match(name)
        if n == '8' and not name.upper().startswith('MSQ-125'):
            brand = None
        if model and n in {'8','9'}:
            device = model.group(1).upper().replace(' ', '-')
        elif n in {'5','6'}:
            return None, 'C08_HinhBoSung_LightStar', 'drawing_context'
        else:
            device = {'2':'ZCT120','3':'CT_500-5A','4':'DayBD01','7':'MSQ-30',
                      '8':'MSQ-125_LienQuan','9':'DayCML'}.get(n, 'C08_HinhBoSung')
        if device == 'DayBD01':
            device = 'BD01'
        if device in {'MSQ-125_LienQuan', 'DayCML'}:
            return None, f'C08_HinhBoSung_{safe(device)}', 'drawing_context'
        return brand, device, 'cùng cụm CAD; mã block cần đối chiếu'
    if zone == 'C12':
        match = MODEL_PREFIX.match(name)
        if name.upper().startswith('EM4H09D'):
            return 'EMIC', 'EM4H09D', 'hình trong vùng C12'
        if match and match.group(1).upper().startswith('RCT'):
            return None, match.group(1).upper(), 'mã RCT đọc từ hình; hãng chưa được xác nhận'
        if match and match.group(1).upper().startswith('MSQ'):
            return None, match.group(1).upper(), 'không gán hãng chỉ từ chữ MSQ'
        return None, 'C12_HinhBoSung', 'drawing_context'
    raise AssertionError(code)

def safe(value):
    value = unicodedata.normalize('NFD', value).replace('Đ', 'D').replace('đ', 'd')
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^A-Za-z0-9._-]+', '_', value).strip('._-')[:72]

device_records = {}
counts = Counter()
expected_items = set()
for row in records:
    brand, device, relation = classify(row)
    parent = TARGET / ('TuLieuBanVe' if relation == 'drawing_context' else safe(brand) if brand else 'TheoLoai')
    parts = device.split('/') if '/' in device else [device]
    device_dir = parent.joinpath(*(safe(part) for part in parts))
    assert device_dir.resolve().is_relative_to(TARGET.resolve())
    role = {'view':'HinhChieu','block':'ThanhPhanCAD',
            'group':'BanVeCum','region':'BanVeVung'}[row['kind']]
    item_dir = device_dir / role / row['id']
    expected_items.add(item_dir.resolve())
    item_dir.mkdir(parents=True, exist_ok=True)
    assets = {}
    for field, filename in (('cad_dxf','ban_ve.dxf'),('preview','xem_truoc.svg')):
        relative = row.get(field)
        if relative:
            source = (SOURCE / relative).resolve()
            assert source.is_relative_to(SOURCE.resolve()) and source.is_file()
            shutil.copy2(source, item_dir / filename)
            assets[field] = filename
    data = {'id':row['id'],'thiet_bi':device,
            'loai_hinh':row['kind'],'ten_hinh':row['name'],'tep':assets}
    if row['kind'] == 'view':
        data['kich_thuoc_hinh_mm'] = cad_size(row)
    (item_dir/'thong_tin.json').write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if relation != 'drawing_context':
        device_records.setdefault(device_dir,[]).append(row)
    counts[row['kind']] += 1

for device_dir, rows in device_records.items():
    brand, model = (None if device_dir.parent.name == 'TheoLoai' else device_dir.parent.name), device_dir.name
    if device_dir.parent.name == 'BienDongBaPha':
        brand = 'LightStar'
    emic = bool(re.fullmatch(r'EM4H0[3-7]',model))
    zero_sequence = 'ZCT' in model
    analysis = {
        'nhom':'Biến dòng điện','hang_xac_nhan':brand,'ten_kieu':model,
        'ban_chat':('Biến dòng thứ tự không (ZCT)' if zero_sequence else
                    'Biến dòng đo lường 3 pha dạng vuông' if brand == 'LightStar' and model == 'Biến dòng vuông' else
                    'Biến dòng đo lường' if emic else 'Biến dòng'),
        'cong_dung':('Phát hiện dòng rò hoặc chạm đất bằng cách đo dòng dư của toàn bộ dây mang điện đi qua lõi; đưa tín hiệu tới rơ le bảo vệ.'
                    if zero_sequence else
                    'Biến đổi dòng sơ cấp lớn thành tín hiệu thứ cấp cho đồng hồ đo điện/thiết bị giám sát.'),
        'vi_tri_lap_dat':('Tại ngăn bảo vệ của tủ điện, bao quanh tất cả dây pha và dây trung tính nếu mạch có trung tính; dây PE không đi qua lõi.'
                          if zero_sequence else
                          'Trong tủ điện hạ thế, quanh thanh cái hoặc dây pha tại ngăn đo lường; thứ cấp nối tới thiết bị đo.'),
        'thong_so':{'dong_so_cap_dinh_muc_A':None,'dong_thu_cap_dinh_muc_A':None,
                    'cap_chinh_xac':None,'cong_suat_VA':None,
                    'ghi_chu':'Tỷ số dòng, cấp chính xác và công suất phụ thuộc biến thể cụ thể.'},
        'cac_hinh_cad':[r['id'] for r in rows],
    }
    if zero_sequence and model == 'ZCT-300A':
        analysis['luu_y_thong_so'] = '300A trong tên kiểu không đủ để kết luận tỷ số biến dòng là 300/5A.'
    explicit_ratio = re.fullmatch(r'(?:P?CT\s*)?(\d+)\s*/\s*(\d+)\s*A', rows[0]['group'], re.I)
    if explicit_ratio and all(r['group'] == rows[0]['group'] for r in rows):
        analysis['thong_so']['dong_so_cap_dinh_muc_A'] = int(explicit_ratio.group(1))
        analysis['thong_so']['dong_thu_cap_dinh_muc_A'] = int(explicit_ratio.group(2))
        analysis['thong_so']['ty_so'] = f'{explicit_ratio.group(1)}/{explicit_ratio.group(2)} A'
    if emic:
        analysis['loai_thiet_bi']='Máy biến dòng một tỷ số.'
        analysis['cau_hinh_dong_san_pham'] = {
            'so_ty_so': 1,
            'dong_thu_cap_tuy_chon_A': [5, 1],
            'ky_hieu_dau_so': {'so_cap': 'P1-P2', 'thu_cap': 'S1-S2'},
        }
    analysis = enrich(analysis, model, brand, rows)
    (device_dir/'thong_tin_thiet_bi.json').write_text(
        json.dumps(analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Previous generated layouts may remain after folder names change. Keep only
# the current paths for these inventory IDs and generated profile documents.
expected_profiles = {(folder/'thong_tin_thiet_bi.json').resolve() for folder in device_records}
for path in TARGET.rglob('thong_tin.json'):
    if path.parent.resolve() in expected_items:
        continue
    stale = path.parent
    assert stale.resolve().is_relative_to(TARGET.resolve())
    assert {p.name for p in stale.iterdir()}.issubset({'thong_tin.json','ban_ve.dxf','xem_truoc.svg'})
    assert json.loads(path.read_text(encoding='utf-8'))['id'] in {r['id'] for r in records}
    shutil.rmtree(stale)
for path in TARGET.rglob('thong_tin_thiet_bi.json'):
    if path.resolve() not in expected_profiles:
        path.unlink()
for folder in sorted((p for p in TARGET.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    if not any(folder.iterdir()):
        folder.rmdir()

assert sum(counts.values()) == 218
print(json.dumps({'records':sum(counts.values()),'by_kind':counts,
                  'device_folders':len(device_records),
                  'emic_models':sorted(p.name for p in (TARGET/'EMIC').iterdir()),
                  'files':len([p for p in TARGET.rglob('*') if p.is_file()])},ensure_ascii=False))

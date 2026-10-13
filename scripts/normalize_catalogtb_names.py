"""Use product names; display geometry and identification candidates separately."""
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'

def normalize(d, category, key):
    old = d.get('ten_san_pham') or d['ten_kieu']
    spec = d.get('thong_so', {})
    brand = d.get('hang_xac_nhan') or ''
    code = d.get('ma_dong_san_pham') or ''
    if category == 'Quạt':
        if key.endswith('_230'): return f'Quạt lọc gió {brand} {code}'.strip()
        if key.endswith('_300'): return 'Bộ lọc gió tủ điện'
        if key.startswith('LuoiGio_'): return 'Lưới thông gió tủ điện'
        return 'Lưới bảo vệ quạt'
    if category == 'Tụ bù':
        return f"Tụ bù {'khô' if 'Kho' in key else 'dầu'} {brand}".strip()
    if category == 'LS':
        if key.startswith('MC_'): kind = 'Khởi động từ'
        elif key.startswith('MT_'): kind = 'Rơ le nhiệt'
        elif key == 'UA_1': kind = 'Tiếp điểm phụ'
        elif key.startswith('BKD'): kind = 'Cầu dao cách ly'
        elif key.startswith('RKN'): kind = 'RCCB'
        elif key.startswith(('RKP', '32KGR', 'BS32')): kind = 'RCBO'
        elif key.startswith(('BKH', 'BKN', 'BKP')): kind = 'MCB'
        else: kind = 'MCCB'
        return f'{kind} LS {code}'.strip()
    if category == 'BienDong':
        if 'ZCT' in old: kind = 'Biến dòng thứ tự không'
        elif 'PCT' in old: kind = 'Biến dòng bảo vệ'
        else: kind = 'Biến dòng đo lường'
        model = code or old.split(' · ')[0]
        model = model.replace('CT_', '').replace('PCT_', '').replace('ZCT_', 'ZCT-').replace('_', ' ')
        model = re.sub(r'(\d+)-5A', r'\1/5 A', model)
        if model.startswith('Biến dòng'): return model
        return ' '.join(v for v in [kind, brand, model] if v)
    special = {
        'DongHoKimNho': 'Đồng hồ đo điện dạng kim',
        'Schneider_PM710': 'Đồng hồ đa năng Schneider PowerLogic PM710',
        'Omega_BE-96_500V': 'Vôn kế Omega BE-96',
        'DSE8610_Candidate': 'Bộ điều khiển máy phát điện',
        'BaoVePha_MatVaLung': 'Rơ le giám sát pha',
    }
    if key in special: return special[key]
    name = old.replace(' · ký hiệu ', ' ').replace(' · nhóm ', ' ')
    name = re.sub(r' · (?:mặt|bích|thân|cỡ|khoảng) .*$', '', name)
    name = re.sub(r' · [\d.,]+(?: × .*| mm)$', '', name)
    name = re.sub(r' [\d.,]+ × [\d.,]+ mm$', '', name)
    name = re.sub(r' kiểu [1-4](?= · | |$)', '', name)
    name = re.sub(r' · cỡ (?:lớn|vừa|nhỏ)$', '', name)
    name = name.replace(' · ứng viên DSE8610', '')
    return name.strip(' ·')

report = []
for p in ROOT.rglob('thong_tin_thiet_bi.json'):
    d = json.loads(p.read_text(encoding='utf-8'))
    old = d.get('ten_san_pham') or d['ten_kieu']
    spec = d.get('thong_so', {})
    category = p.relative_to(ROOT).parts[0]
    name = normalize(d, category, p.parent.name)
    # Keep distinguishing sizes and electrical configurations below the product name.
    hints = []
    for field in ('kich_thuoc_mat_truoc_mm', 'kich_thuoc_hinh_chieu_mm', 'kich_thuoc_hinh_mm'):
        if spec.get(field): hints.append(str(spec[field]) + ' mm'); break
    for field in ('so_cuc', 'dien_ap_dinh_muc'):
        if spec.get(field): hints.append(str(spec[field]))
    if not hints:
        m = re.search(r'[\d.,]+ × [\d.,]+ mm', old)
        if m: hints.append(m.group())
    d['quy_cach_hien_thi'] = ' · '.join(hints)
    d['ten_kieu'] = d['ten_san_pham'] = name
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if name != old: report.append({'thu_muc': p.parent.relative_to(ROOT).as_posix(), 'cu': old, 'moi': name})
(ROOT/'kiem_tra_ten_thiet_bi.json').write_text(json.dumps({'so_ho_so': 325, 'ten_da_sua': report},ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
print('Product names updated:', len(report))

"""Short display names and explicit, searchable identities for LS/Mitsubishi."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data/CatalogTB'
SYNONYMS = {
    'MCB': ['aptomat tep', 'aptomat tép', 'cầu dao tự động', 'miniature circuit breaker'],
    'MCCB': ['aptomat khoi', 'aptomat khối', 'molded case circuit breaker'],
    'RCCB': ['cầu dao chống rò', 'chống giật', 'residual current circuit breaker'],
    'RCBO': ['chống rò và quá dòng', 'chống giật', 'residual current overcurrent breaker'],
    'ELCB': ['cầu dao chống rò', 'earth leakage circuit breaker'],
    'Contactor': ['công tắc tơ', 'khởi động từ', 'khoi dong tu'],
    'Thermal Relay': ['rơ le nhiệt', 'relay nhiệt', 'overload relay'],
    'Isolator': ['cầu dao cách ly', 'switch disconnector'],
    'Aux Contact': ['tiếp điểm phụ', 'auxiliary contact'],
}

def normalize():
    count = 0
    for brand in ('LS', 'Mitsubishi'):
        for path in sorted((ROOT / brand).rglob('thong_tin_thiet_bi.json')):
            d = json.loads(path.read_text(encoding='utf-8'))
            # New source references have no verified model/brand identity yet.
            if path.parent.name.startswith('SRC_') and d.get('needs_review'):
                continue
            code = d.get('ma_dong_san_pham') or path.parent.name
            kind = d.get('ban_chat', '')
            if 'tiếp điểm phụ' in kind: category = 'Aux Contact'
            elif 'nhiệt' in kind: category = 'Thermal Relay'
            elif 'Khởi động từ' in kind or path.parent.name.startswith('S_T'): category = 'Contactor'
            elif 'cách ly' in kind: category = 'Isolator'
            elif 'RCBO' in kind or code == 'BS32c': category = 'RCBO'
            else: category = next((k for k in ('MCCB', 'RCCB', 'MCB', 'ELCB') if k in kind), None)
            if not category: raise ValueError((path, kind))
            poles = d.get('thong_so', {}).get('so_cuc') or None
            if poles is not None:
                poles = str(poles)
                if poles.isdigit(): poles += 'P'
            models = [v.strip() for v in code.split('/')]
            # Metasol source labels denote frame families, not complete order codes.
            frame = re.search(r'\b(100|125|250|400|800)\b', code) if path.parent.name.startswith('Metasol') else None
            if frame:
                models = [v + frame.group(1) + 'AF' for v in re.findall(r'AB[NHS]', code)]
            display_code = '/'.join(models)
            dc = brand == 'Mitsubishi' and code in ('NF800-SDW', 'NF1250-SDW', 'NF1600-SDW') and poles == '2P'
            name = f'{category} {brand} {display_code}' + (f' · {poles}' if poles else '') + (' · DC' if dc else '')
            aliases = [name, code, d.get('ten_san_pham', ''), d.get('hang_xac_nhan', ''), *models, *SYNONYMS[category]]
            aliases += [re.sub(r'[^a-zA-Z0-9]', '', v) for v in models]
            d['ten_kieu'] = d['ten_san_pham'] = name
            d['tu_khoa_tim_kiem'] = list(dict.fromkeys(v for v in aliases if v))
            d['nhan_dien_ai'] = {**d.get('nhan_dien_ai', {}),
                'loai_thiet_bi_code': category, 'hang': brand, 'cac_ma_dong_san_pham': models,
                'so_cuc': poles, 'loai_nguon': 'DC' if dc else None,
                'pham_vi_ma': 'family_frame' if frame else 'model_or_shared_cad_family',
                'ma_dat_hang_da_chon': None,
                'quy_tac': 'Tra từng mã trong nhóm; CAD chung không xác nhận cùng thông số điện. Chọn cấu hình và mã đặt hàng trước thi công. Giá trị null là chưa xác định.'}
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            count += 1
    return count

if __name__ == '__main__': print('Normalized', normalize(), 'profiles')

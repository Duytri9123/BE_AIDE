"""Publish ABB family configuration choices without approving electrical/CAD identity."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data' / 'CatalogTB'
CAD_SOURCE = 'https://abb-control-products.partcommunity.com/3d-cad-models/molded-case-circuit-breakers-tmax-xt-abb-low-voltage-systems?info=abb_ww%2Flow_voltage%2Fbreakers%2Fmodular20case20circuit20breakers20tmax20xt'


def update():
    rows = json.loads((ROOT / 'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    report = []
    for path in sorted((CATALOG / 'ABB/ThietBi').glob('XT[1-4]_[34]P/thong_tin_thiet_bi.json')):
        profile = json.loads(path.read_text(encoding='utf8'))
        family = profile['ma_dong_san_pham']
        poles = profile['thong_so']['so_cuc']
        choices = [r for r in rows if r.get('brand') == 'ABB' and r.get('category') == 'MCCB'
                   and (r.get('specifications') or {}).get('Họ thiết bị') == family
                   and (r.get('specifications') or {}).get('Số cực') == poles]
        options = []
        for row in choices:
            specs = dict(row.get('specifications') or {})
            specs['Tên hàng'] = row['item_name']
            options.append(dict(brand='ABB', model=row['sku'], source_row_id=row['id'],
                                specifications=specs, source_url=row.get('source_url'),
                                source_page=row.get('source_page'), basis='family_configuration_option'))
        refs = profile.setdefault('catalog_tham_khao', {})
        refs['options'] = [o for o in refs.get('options', []) if o.get('basis') != 'family_configuration_option'] + options
        refs['category'] = 'MCCB'
        profile['quy_tac_dung_chung_cad'] = {
            'family': family, 'poles': poles, 'relationship': 'one_geometry_many_configuration_options',
            'electrical_rating_from_geometry': False,
            'requirements': ['Đúng số cực, kiểu cố định/rút kéo, đầu nối và phụ kiện',
                             'Đối chiếu In, Icu/Ics tại điện áp làm việc của từng mã',
                             'Chỉ dùng chung mặt sau khi đối chiếu kích thước của biến thể'],
            'supplier_cad_source': CAD_SOURCE, 'checked_at': '2026-10-20',
            'new_faces_imported': any(str(v.get('id_hinh_goc','')).startswith('ABB-OFFICIAL-') for v in profile.get('cad_don',[]))}
        profile['tu_khoa_tim_kiem'] = list(dict.fromkeys(profile.get('tu_khoa_tim_kiem', []) +
                                                      [r['item_name'] for r in choices] + [r['sku'] for r in choices]))
        for view in profile.get('cad_don', []):
            view['nhan_hien_thi'] = f"ABB · MCCB · {family} · {poles} · {view['huong_nhin']}"
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        report.append({'profile': path.relative_to(CATALOG).as_posix(), 'configuration_count': len(options),
                       'faces': [v['huong_nhin'] for v in profile.get('cad_don', [])]})
    output = ROOT / 'docs/abb-cad-configurations-2026-10-20.json'
    output.write_text(json.dumps({'profiles': report, 'source': CAD_SOURCE,
        'new_faces_imported': False,
        'acquisition_status': 'Legacy ABB 2D DownloadCenter links return HTTP 404; existing verified faces retained.'},
        ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f"Updated {len(report)} ABB profiles; {sum(r['configuration_count'] for r in report)} configuration choices")


if __name__ == '__main__':
    update()

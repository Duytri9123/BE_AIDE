"""Promote explicitly named CAD components to browsable, unpriced catalog entries."""
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def component_type(name):
    key = name.casefold()
    for pattern, category in (
        (r'^(banlela|bl012-front|bl012-side|bl036-side|tv-\w*bl)', 'Bản lề'),
        (r'^(den (do|vang|xanh)|warning light)', 'Đèn báo'),
        (r'^(ampere-meter|von-to|von-nho|am-nho|congto)', 'Đồng hồ'),
        (r'^(khoa |khoa[Vv]|khoado|ms722|ms303|ms308|ms325)', 'Khóa tủ'),
        (r'^(bulong|bulon|ecu|tai cau|tai treo|moccau)', 'Phụ kiện cơ khí'),
        (r'^(domino|tb-)', 'Cầu đấu'),
    ):
        if re.search(pattern, key): return category
    return None

if __name__ == '__main__':
    rows = []
    for file in sorted((ROOT/'data/device_layouts').glob('*/manifest.json')):
        for item in json.loads(file.read_text(encoding='utf8'))['items']:
            category = component_type(item['name'])
            if not category: continue
            rows.append(dict(ma='CAD:'+item['id'], n=category+' · '+item['name'],
                brand='unspecified' if item['brand']=='Chưa xác định hãng' else item['brand'],
                brand_display=item['brand'], series='Linh kiện CAD · '+file.parent.name,
                t=category, g=None, _verified=False,
                cad={'asset_id':item['id']}, source={'file':item['source_file'],'block':item['name']},
                note='Hình học CAD nguồn; chưa xác minh model, hướng nhìn và thông số đặt hàng.'))
    (ROOT/'data/catalog_cad_components.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    print(len(rows))

"""Write a reviewable inventory of the combined drawing and backup."""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.cad.library_taxonomy import classify, explicit_brands


def write_inventory():
    items, groups = [], defaultdict(list)
    for library in ('combined', 'source_cells', 'source_components'):
        data = json.loads((ROOT / f'data/device_layouts/{library}/manifest.json').read_text(encoding='utf8'))
        for row in data['items']:
            brands = explicit_brands(row.get('category', '') + ' ' + row['name'])
            item = {**row, 'library': library, **classify(row['name'], row.get('category', '')),
                    'brand': brands[0] if len(brands) == 1 else row['brand']}
            items.append(item)
            groups[(item['kind'], item['group'])].append(item)
    labels = {'device': 'Thiết bị', 'accessory': 'Phụ kiện', 'unclassified': 'Chưa phân loại'}
    lines = ['# Kiểm kê thư viện TỔNG HỢP 1', '',
             'Nguồn: TỔNG HỢP 1.dwg và TỔNG HỢP 1.bak. Đã đối chiếu SHA-256 bản DWG/BAK dùng chuyển đổi với file gốc.', '',
             '319 block có tên, 221 thành phần tách từ ô bảng, 54 ô nguồn. Đây là số mục hình học, không phải số model riêng biệt. Các mục có thể dùng chung CAD.', '',
             'Giữ nguyên ô nguồn khi có hình rời chưa xác định được ranh giới thiết bị. Tên chưa rõ được giữ trong Chưa phân loại; không tự gán hãng hoặc dựng thêm mặt chiếu.', '',
             '| Nhóm chính | Loại | Số mục CAD |', '|---|---|---:|']
    for (kind, group), rows in sorted(groups.items()):
        lines.append(f'| {labels[kind]} | {group} | {len(rows)} |')
    for (kind, group), rows in sorted(groups.items()):
        lines += ['', f'## {labels[kind]} — {group}', '', '| Tên nguồn | Hãng ghi rõ | Dữ liệu | ID CAD |', '|---|---|---|---|']
        for row in rows:
            lines.append(f"| {row['name'].replace('|', '/')} | {row['brand']} | {'Ô nguồn' if row['library']=='source_cells' else 'Block'} | {row['id']} |")
    (ROOT / 'data/library_inventory.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    (ROOT / 'data/library_inventory.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf8')
    print({label: sum(i['kind'] == key for i in items) for key, label in labels.items()})


if __name__ == '__main__':
    write_inventory()

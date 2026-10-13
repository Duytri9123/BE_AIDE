"""Import the five-column protection-device tables of the April 2026 Hyundai book.

Only actual cell geometry is used for merged fields; other layouts stay unimported.
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

SOURCE_URL = 'https://www.saigonelectric.vn/images/prices/HYUNDAI_2026.2.pdf'


def import_book(source):
    root = Path(__file__).resolve().parents[1]
    doc = pymupdf.open(source)
    checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    items = []
    for number in (2, 3, 6):
        page = doc[number-1]
        # These pages' first tables share the explicitly labelled five columns.
        table = page.find_tables().tables[0]
        rows = table.extract()
        header_index = next(i for i, row in enumerate(rows)
                            if row[0] == 'Mã hàng' and len(row) == 5)
        boundaries = table.rows[header_index].cells
        columns = ['Tên hàng', 'Số cực', 'Dòng định mức In (A)', 'Icu (kA)', 'Giá bán']
        section_poles = ''
        for index, row in enumerate(rows[header_index+1:], header_index+1):
            if not row[-1] or not re.fullmatch(r'\d{1,3}(?:,\d{3})+', row[-1].strip()):
                section = re.match(r'^MCCB\s+(\dP)\b', row[0] or '')
                section_poles = section[1] if section else ''
                continue
            cells = table.rows[index].cells
            y = (cells[-1][1]+cells[-1][3])/2
            values = []
            for col, value in enumerate(row):
                if value is None:
                    left, _, right, _ = boundaries[col]
                    x = (left+right)/2
                    containing = [rect for previous in table.rows for rect in previous.cells
                                  if rect and rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]
                                  and abs(rect[0]-left) < 2 and abs(rect[2]-right) < 2]
                    value = page.get_textbox(containing[0]) if containing else ''
                lines = [re.sub(r'\s+', ' ', part).strip() for part in (value or '').splitlines()]
                values.append(' '.join(dict.fromkeys(part for part in lines if part)))
            model = values[0]
            if not values[1] and section_poles:
                values[1] = section_poles  # Explicit section heading in this PDF.
            if not re.match(r'^HG[MDPE]\d', model):
                continue
            category = 'MCB' if model.startswith('HGD') else 'ELCB' if model.startswith('HGE') else 'MCCB'
            row_id = hashlib.sha1(f'{number}:{index}:{model}'.encode()).hexdigest()[:16]
            items.append({'id': 'hyundai-pdf:'+row_id, 'sku': model, 'item_name': model,
                          'name': model, 'brand': 'Hyundai', 'category': category,
                          'group': category, 'price': int(values[-1].replace(',', '')), 'currency': 'VND',
                          'columns': columns, 'cells': values,
                          'specifications': dict(zip(columns[1:-1], values[1:-1])),
                          'source_kind': 'supplier_pricebook', 'source_label': 'Hyundai 2026 · Điện Sài Gòn',
                          'source_url': SOURCE_URL, 'source_page': number, 'source_sha256': checksum,
                          'edition': '2026', 'effective_date': '2026-04-20', 'vat_status': 'excluded',
                          'checked_at': datetime.now(timezone.utc).isoformat(),
                          'price_note': 'Giá niêm yết; chưa gồm VAT. Thông số trống cần đối chiếu nguồn.'})
    path = root/'app/data/supplier_pricebooks.json'
    payload = json.loads(path.read_text(encoding='utf8'))
    payload['items'] = [item for item in payload['items'] if item['brand'] != 'Hyundai']+items
    payload['manufacturers']['Hyundai'] = {'imported_pages': [2, 3, 6], 'total_source_pages': len(doc),
                                         'coverage': 'five_column_protection_tables_only'}
    pending = path.with_suffix('.json.tmp')
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    pending.replace(path)
    print(json.dumps({'accepted_rows': len(items), 'pages_imported': [2, 3, 6], 'source_pages': len(doc)}))


if __name__ == '__main__':
    import_book(sys.argv[1])

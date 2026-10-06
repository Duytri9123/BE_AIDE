"""Read every actual price cell from the supplied LS PDF table extraction."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP/LS_D02_DU_LIEU_MOI'
TABLES = BASE / 'price_tables_source.json'
if not TABLES.exists():
    TABLES.write_bytes((ROOT / 'tmp/ls_tables.json').read_bytes())
pages = json.loads(TABLES.read_text(encoding='utf8'))
money = re.compile(r'^\d{1,3}(?:,\d{3})+$')
rows = []
for page_number, tables in enumerate(pages, 1):
    for table_number, table in enumerate(tables, 1):
        width = max(len(row) for row in table)
        stride = 4 if width in (4, 8) else width
        headings = [''] * ((width + stride - 1)//stride)
        for source_row, cells in enumerate(table, 1):
            for part, start in enumerate(range(0, width, stride)):
                fields = list(cells[start:start+stride])
                fields += [None] * (stride-len(fields))
                title = (fields[0] or '').strip()
                price = (fields[-1] or '').strip()
                if title and not price and title.lower() not in ('tên hàng', 'ten hang'):
                    headings[part] = title
                if not title or not money.fullmatch(price):
                    continue
                if title.lower().startswith(('tên hàng','ten hang')):
                    continue
                raw_name = re.sub(r'\s+', ' ', title)
                code_match = re.match(r'^[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z0-9-]+)?', raw_name)
                rows.append({
                    'row_id': len(rows)+1,
                    'model': (code_match.group(0).split()[0] if code_match else raw_name).upper(),
                    'name_pdf': raw_name,
                    'in_a_pdf': re.sub(r'\s+', ' ', fields[1] or '').strip() if stride >= 3 else None,
                    'icu_ka_pdf': re.sub(r'\s+', ' ', fields[2] or '').strip() if stride == 4 else None,
                    'price_vnd_ex_vat': int(price.replace(',','')),
                    'section_pdf': headings[part],
                    'page': page_number,
                    'table': table_number,
                    'source_row': source_row,
                    'source': 'Bang gia LS ap dung ngay 01-10-2026.pdf',
                    'effective_date': '2026-10-01'
                })
(BASE/'price_index.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'price_rows':len(rows),'pages':len(pages)}))

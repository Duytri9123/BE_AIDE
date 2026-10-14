"""Import the explicitly VINAKIP-labelled MCCB/2P1E page, excluding OKOM."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://kimquang.vn/wp-content/uploads/2022/07/bang-gia-cau-dao-hop-vinakip.pdf'


def extract(source):
    doc = pymupdf.open(source)
    assert '01 - 07 - 2026' in doc[0].get_text()
    text = doc[17].get_text()
    assert 'NHÃN HIỆU VINAKIP' in text and 'OKOM' not in text
    checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    rows = []
    for name, code, amount in re.findall(r'(Aptomat [^\n]+)\n(AT \d+)\n(\d{1,3}(?:\.\d{3})+) đ', text):
        current = re.search(r'(\d+)A\b', name)
        if not current:
            continue
        kind = 'MCCB' if re.search(r'\bVK[EN]\b', name) else 'MCB'
        spec = {'In (A)': current[1]}
        if '2P1E' in name:
            spec['Số cực'] = '2P'
        rows.append(dict(id='vinakip-pdf:'+code.replace(' ', ''), sku=code, item_name=name,
                         name=name, brand='Vinakip', category=kind, group=kind,
                         price=int(amount.replace('.', '')), currency='VND', specifications=spec,
                         columns=['Tên hàng', 'Series', 'Giá bán'], cells=[name, code, amount],
                         source_kind='supplier_pricebook', source_label='Vinakip · 2026',
                         source_url=URL, source_page=18, source_sha256=checksum,
                         source_line=name+' | '+code+' | '+amount+' đ', edition='2026',
                         effective_date='2026-07-01', vat_status='included',
                         checked_at=datetime.now(timezone.utc).isoformat(),
                         price_note='Bảng giá áp dụng 01/07/2026, đã bao gồm VAT.'))
    return rows


if __name__ == '__main__':
    rows = extract(ROOT/'tmp/vinakip-pricebook.pdf')
    path = ROOT/'app/data/supplier_pricebooks.json'
    data = json.loads(path.read_text(encoding='utf8'))
    data['items'] = [r for r in data['items'] if not r['id'].startswith('vinakip-pdf:')]+rows
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('Vinakip', len(rows))

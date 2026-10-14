"""Publish explicit ABB Vietnam 2026 rows, retaining PDF page and checksum."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

SOURCE = 'https://library.e.abb.com/public/8fa0d161aec14871ae110caa57108c49/9AKK108472A7059_vi_B_EL%20Vietnam%20Master%20price%20list%202026%20%28VIE%29.pdf'


def extract_rows(source):
    doc = pymupdf.open(source)
    if len(doc) != 218 or '2026' not in doc[28].get_text():
        raise ValueError('Expected reviewed ABB Vietnam 2026 edition, 218 pages')
    checked = datetime.now(timezone.utc).isoformat()
    checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    rows = []

    def add(page, line, model, sku, category, poles, amps, price, family=None):
        spec = {'Mã đặt hàng': sku, 'Số cực': poles, 'In (A)': str(amps)}
        if family:
            spec['Họ thiết bị'] = family
        if category == 'CONTACTOR':
            spec['Mã thân'] = model.rsplit('-', 1)[0]
        rows.append(dict(id='abb-2026:'+sku, sku=sku, item_name=f'{model} {poles} {amps}A',
                         name=f'{model} {poles} {amps}A', brand='ABB', category=category,
                         group=category+' · '+(family or model.split('-')[0]), price=int(price.replace(',', '')),
                         currency='VND', specifications=spec,
                         columns=['Tên hàng', 'Mã đặt hàng', 'Số cực', 'In (A)', 'Giá bán'],
                         cells=[f'{model} {poles} {amps}A', sku, poles, str(amps), price],
                         source_kind='supplier_pricebook', source_label='ABB Việt Nam 2026',
                         source_url=SOURCE, source_page=page, source_sha256=checksum,
                         source_line=line, edition='2026', effective_date=None,
                         checked_at=checked, vat_status='excluded',
                         price_note='Giá niêm yết ABB Việt Nam 2026 chưa gồm VAT; chọn đúng mã và cấu hình.'))

    for page in range(28, 32):
        sheet = doc[page-1]
        # The reviewed table's first ordering-code column starts near x=330;
        # its second column starts beyond x=440. Never infer poles by pair count.
        positions = {w[4]: w[0] for w in sheet.get_text('words') if re.fullmatch(r'1SDA\w+', w[4])}
        for line in sheet.get_text(sort=True).splitlines():
            model = re.search(r'\b(A[0-3][A-Z])\s+\d+\s+(TMF|TMD|TMA)\s+(\d+)-\d+', line)
            if not model:
                continue
            for sku, price in re.findall(r'\b(1SDA\w+)\s+(\d{1,3}(?:,\d{3})+)\b', line):
                x = positions[sku]
                if not (320 < x < 380 or 440 < x < 500):
                    raise ValueError(f'Unexpected ordering-code column: page {page}, {sku}, {x}')
                pole = ('1P' if x < 400 else '2P') if page == 28 else ('3P' if x < 400 else '4P')
                add(page, line.strip(), model[1]+' '+model[2], sku, 'MCCB', pole, model[3], price, model[1][:2])

    for page in (141, 142, 143):
        for line in doc[page-1].get_text(sort=True).splitlines():
            m = re.search(r'\b((?:SH|SY|S)20([1-4])[LM]?-C(\d+))\s+(2CDS\w+)\s+(\d{1,3}(?:,\d{3})+)\s*$', line)
            if m:
                family = ('SH200' if m[1].startswith('SH') else 'SY200' if m[1].startswith('SY') else 'S200')
                add(page, line.strip(), m[1], m[4], 'MCB', m[2]+'P', m[3], m[5], family)
    for page in range(113, 118):
        for line in doc[page-1].get_text(sort=True).splitlines():
            m = re.search(r'\b(AX(\d{2,3})-(\d)\d-\d+-\d+)\s+(1S(?:BL|FL)\w+)\s+(\d{1,3}(?:,\d{3})+)\s*$', line)
            if m:
                add(page, line.strip(), m[1], m[4], 'CONTACTOR', m[3]+'P', m[2], m[5])
    for line in doc[116].get_text(sort=True).splitlines():
        m = re.search(r'(\d+(?:\.\d+)?)\s+\.\.\.\s+(\d+(?:\.\d+)?)\s+(TA\d+DU-[\d.]+M?)\s+(1SAZ\w+)\s+(\d{1,3}(?:,\d{3})+)\s*$', line)
        if not m:
            continue
        family=m[3].split('-')[0]
        add(117,line.strip(),m[3],m[4],'THERMAL_RELAY','',m[2],m[5],family)
        row=rows[-1]
        row['item_name']=row['name']=m[3]
        row['specifications'].pop('In (A)')
        row['specifications'].pop('Số cực')
        row['specifications']['Dải chỉnh định (A)']=m[1]+'–'+m[2]
        row['columns']=['Tên hàng','Mã đặt hàng','Dải chỉnh định (A)','Giá bán']
        row['cells']=[m[3],m[4],m[1]+'–'+m[2],m[5]]
    assert rows and len({r['sku'] for r in rows}) == len(rows), 'Duplicate ABB ordering codes'
    return rows


def import_book(source):
    rows = extract_rows(source)
    root = Path(__file__).resolve().parents[1]
    target = root/'app/data/supplier_pricebooks.json'
    payload = json.loads(target.read_text(encoding='utf8'))
    payload['items'] = [r for r in payload['items'] if not r['id'].startswith('abb-2026:')]+rows
    payload['manufacturers']['ABB'] = {'models': {r['sku']: [r['id']] for r in rows}}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'accepted_rows': len(rows), 'categories': sorted({r['category'] for r in rows})}))


if __name__ == '__main__':
    import_book(sys.argv[1])

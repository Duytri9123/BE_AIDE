"""Import reviewed PDF price columns; ambiguous spatial pairings stay unpublished."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
BOOKS = {
    'idec': ('IDEC', '2025', 'https://www.saigonelectric.vn/images/prices/IDEC_04.2025_R4.2.pdf'),
    'fuji': ('Fuji Electric', '2025', 'https://www.saigonelectric.vn/images/prices/Fuji_2025_MNE.2.pdf'),
    'mikro': ('Mikro', '2026', 'https://www.saigonelectric.vn/images/prices/MIKRO_15-01-2026.2.pdf'),
    'shihlin': ('Shihlin', '2026', 'https://www.saigonelectric.vn/images/prices/SHIHLIN_01.02.2026.2.pdf'),
}


def category(key, code):
    if key == 'idec':
        return 'LIGHT' if re.match(r'(YW1P|AL\dM-P)', code) else 'SELECTOR_SWITCH' if re.match(r'(YW1[SK]|AS\d)', code) else 'PUSHBUTTON' if re.match(r'(YW1B|[A-Z]L?B?6M)', code) else 'RELAY' if re.match(r'(R[HY]|RU|RQ|RF)', code) else 'ACCESSORY'
    if key == 'fuji':
        return 'MCCB' if code.startswith('BW') else 'ACB' if code.startswith('BT3') else 'CONTACTOR' if code.startswith('SC') else 'THERMAL_RELAY' if code.startswith('TR') else 'INVERTER' if code.startswith('FRN') else 'ACCESSORY'
    if key == 'mikro':
        return 'POWER_FACTOR_CONTROLLER' if code.startswith('PFR') else 'PHASE_RELAY' if code.startswith('MX100') else 'VOLTAGE_RELAY' if code.startswith(('MX', 'MU')) else 'METER' if code.startswith(('DPM', 'DM')) else 'CT' if code.startswith('ZCT') else 'EARTH_FAULT_RELAY' if re.match(r'(NX201|N201|R201|RX232)', code) else 'EARTH_LEAKAGE_RELAY' if re.match(r'(DIN|N301|RX300|RX330|R301)', code) else 'RELAY'
    return 'MCCB' if code.startswith('BM') else 'ELCB' if code.startswith('BL') else 'CONTACTOR' if code.startswith('S-P') else 'THERMAL_RELAY' if code.startswith('TH-P') else 'MCB' if code.startswith('BHA') else 'ACCESSORY'


def extract(key, source):
    brand, edition, url = BOOKS[key]
    doc = pymupdf.open(source)
    checksum = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    checked = datetime.now(timezone.utc).isoformat()
    rows = []
    for number, page in enumerate(doc, 1):
        words = page.get_text('words')
        text = page.get_text()
        vat = 'included' if re.search(r'bao gồm.*VAT', text, re.I) else 'excluded' if re.search(r'chưa.*(?:VAT|GTGT)', text, re.I) else 'unknown'
        for amount in words:
            if not re.fullmatch(r'\d{1,3}(?:,\d{3})+', amount[4]):
                continue
            x, y = amount[0], amount[1]
            if x < (240 if key == 'shihlin' else 470):
                continue
            if key == 'shihlin':
                left, right = (25, 115) if x < 320 else (300, 400)
            elif key == 'mikro':
                left, right = 90, 205
            elif key == 'idec':
                left, right = 115, 300
            else:
                left, right = 295, 475
            # Mikro model cells wrap footnote references below the code;
            # their centered price baseline can sit 6.7 pt below the model.
            tolerance = 8 if key == 'mikro' else 3
            tokens = sorted([w for w in words if left <= w[0] < right and abs(w[1]-y) < tolerance], key=lambda w:(round(w[1]/3),w[0]) if key == 'mikro' else (0,w[0]))
            raw = ' '.join(w[4] for w in tokens)
            normalized = re.sub(r'\s+', '', raw)
            patterns = {
                'idec': r'(?:YW\d[A-Z]|[A-Z]{1,3}\d|R[HYUQF])[-A-Z0-9./]+',
                'fuji': r'(?:BW\d|BT3|SC[-\d]|TR[-\d]|FRN\d)[-A-Z0-9./]+',
                'mikro': r'(?:PFR\d|MX\d|MU\d|N\d|RX\d|R\d|DPM\d|DM\d|ZCT\d|MK\d|DIN\d)[-A-Z0-9./]+',
                'shihlin': r'(?:BM|BL)\d+[a-z]?-[A-Z]+',
            }
            candidate = raw if key == 'fuji' else normalized
            match = re.match(patterns[key], candidate)
            if not match:
                continue
            code = match[0]
            if key == 'fuji':
                suffix = re.match(re.escape(code)+r'\s+(M[123])(?:\s|$)', raw)
                if suffix:
                    code += ' '+suffix[1]
            # Never attach a price to two distinct model tokens on one row.
            if len(re.findall(patterns[key], candidate)) != 1:
                continue
            row_words = sorted([w for w in words if abs(w[1]-y) < 3 and (key != 'shihlin' or (w[0] < 300) == (x < 320))], key=lambda w:w[0])
            detail = ' '.join(w[4] for w in row_words if w[0] < x)
            kind = category(key, code)
            pole = re.search(r'(?:^|\s|-)\b([1-4])P\b', detail)
            spec = {'Dòng trong bảng giá': detail}
            if pole:
                spec['Số cực'] = pole[1]+'P'
            if key == 'mikro':
                spec['Họ thiết bị'] = code.split('-')[0]
            if key == 'shihlin':
                spec['Họ thiết bị'] = re.match(r'[A-Z]+\d+', code)[0]
            price = int(amount[4].replace(',', ''))
            identity = f'{key}:{edition}:{number}:{round(x,1)}:{round(y,1)}:{code}:{pole[1] if pole else ""}'
            rows.append(dict(id='extra-pdf:'+hashlib.sha1(identity.encode()).hexdigest()[:20], sku=code,
                             item_name=code+(f' {pole[1]}P' if pole else ''), name=code,
                             brand=brand, category=kind, group=kind, price=price, currency='VND',
                             specifications=spec, columns=['Tên hàng', 'Thông tin theo bảng giá', 'Giá bán'],
                             cells=[code, detail, amount[4]], source_kind='supplier_pricebook',
                             source_label=f'{brand} · {edition}', source_url=url, source_page=number,
                             source_sha256=checksum, source_line=detail+' '+amount[4], edition=edition,
                             effective_date='2026-01-15' if key == 'mikro' else '2026-02-01' if key == 'shihlin' else None,
                             checked_at=checked, vat_status=vat,
                             price_note=f'Bản công bố {edition}; thông số và cấu hình theo dòng nguồn, không suy diễn thông số thiếu.'))
    unique = {}
    for row in rows:
        if row['id'] in unique:
            assert unique[row['id']]['cells'] == row['cells'], 'Conflicting overlapping PDF price rows'
        unique[row['id']] = row
    return list(unique.values())


def main():
    path = ROOT/'app/data/supplier_pricebooks.json'
    payload = json.loads(path.read_text(encoding='utf8'))
    imported = []
    for key in BOOKS:
        rows = extract(key, ROOT/f'tmp/{key}-pricebook.pdf')
        print(key, len(rows))
        imported.extend(rows)
    urls = {book[2] for book in BOOKS.values()}
    payload['items'] = [r for r in payload['items'] if not (r['id'].startswith('extra-pdf:') and r.get('source_url') in urls)]+imported
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()

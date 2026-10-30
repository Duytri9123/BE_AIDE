"""Import the user's DIKA June 2026 CHINT list, preserving existing reviewed books.

One record per numeric price cell. Grouped currents and wildcard model suffixes
remain as printed; neither order codes nor coil/colour combinations are invented.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SOURCE_KEY = 'chint-dika-2026-06'
SOURCE_SHA = 'd40237b3c908363ec273e91849b59f3b069ea644f3c79214cf6091773fd07def'
MONEY = re.compile(r'^\d{1,3}(?:,\d{3})+$')


def extract(source):
    source = Path(source)
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    if checksum != SOURCE_SHA:
        raise ValueError('This layout was reviewed only for the supplied June 2026 PDF.')
    doc = pymupdf.open(source)
    if len(doc) != 11:
        raise ValueError('Unexpected page count')
    tables = {i + 1: [t.extract() for t in page.find_tables()] for i, page in enumerate(doc)}
    rows = []
    checked = datetime.now(timezone.utc).isoformat()

    def add(page, table, index, column, model, category, group, specs):
        raw = (tables[page][table][index][column] or '').strip()
        if not MONEY.fullmatch(raw):
            return
        specs = {k: re.sub(r'\s+', ' ', str(v)).strip() for k, v in specs.items() if v}
        # Model names identify the printed family; specifications identify the offer.
        columns = ['Tên hàng', *specs, 'Đơn giá gốc chưa VAT']
        rows.append({
            'id': f'{SOURCE_KEY}:{page}:{table}:{index}:{column}',
            'sku': model, 'item_name': model, 'name': model, 'brand': 'CHINT',
            'category': category, 'group': group, 'price': int(raw.replace(',', '')),
            'currency': 'VND', 'specifications': specs, 'columns': columns,
            'cells': [model, *specs.values(), raw], 'source_kind': 'supplier_pricebook',
            'source_label': 'Bảng giá CHINT T6-2026 · DIKA',
            'source_url': '/device-catalog/documents/' + SOURCE_KEY,
            'source_page': page, 'source_sha256': checksum,
            'source_cell': {'table': table, 'row': index, 'column': column},
            'edition': '2026-06', 'effective_date': None, 'checked_at': checked,
            'vat_status': 'excluded',
            'vat_evidence': 'User confirmed on 2026-10-26: PDF prices exclude VAT.',
            'discount_applied_percent': 0,
            'price_note': 'Giá gốc trong PDF, chưa VAT; không áp dụng CK51% theo xác nhận của người dùng ngày 26/10/2026.',
        })

    # Page 2: independent current lists crossed with each printed pole-price cell.
    for table, model, mapping, first in [
        (0, 'NXB-63', {4:'1P', 5:'2P', 6:'3P', 8:'4P'}, 3),
        (1, 'NXB-125', {5:'1P', 6:'2P', 7:'3P', 10:'4P'}, 3),
    ]:
        for i, r in enumerate(tables[2][table][first:], first):
            for column, poles in mapping.items():
                add(2, table, i, column, model, 'MCB', model,
                    {'In (A)': r[0].strip().rstrip(','), 'Số cực': poles,
                     'Icu (A)': '6000' if model == 'NXB-63' else '10000'})
    for i, r in enumerate(tables[3][0][3:], 3):
        add(3, 0, i, 5, r[3], 'MCCB', 'NXM', {'In (A)':r[0], 'Icu (kA)':r[2], 'Số cực':'3P'})

    # Page 4: two distinct coil offers, even when their amounts are equal.
    for i, r in enumerate(tables[4][0][4:], 4):
        for col, coil in [(15,'220VAC'), (18,'380VAC')]:
            add(4, 0, i, col, r[14], 'CONTACTOR', 'NXC',
                {'In':r[3], 'Công suất tại 380/415/440V':r[0], 'Số cực':'3P', 'Điện áp cuộn hút':coil})

    model = fit = None
    for i, r in enumerate(tables[5][0][2:], 2):
        model, fit = r[5] or model, r[3] or fit
        add(5, 0, i, 6, model, 'THERMAL_RELAY', 'NXR', {'Dải chỉnh định Ir (A)':r[0], 'Phù hợp':fit})
    for i in (2,3,4):
        r = tables[5][1][i]
        add(5, 1, i, 7, r[4], 'AUX_CONTACT', 'Phụ kiện contactor', {'Tiếp điểm':r[1], 'Vị trí lắp':'Mặt' if i<4 else 'Cạnh'})
    for i, model in [(7,'MI-5'), (8,'MI-6'), (9,'MI-7')]:
        add(5, 1, i, 7, model, 'INTERLOCK', 'Phụ kiện contactor', {'Phù hợp':tables[5][1][i][1]})

    for i in (2,3,4,5,8,9,10,11):
        r = tables[6][1][i]
        spec = {'In':r[0]}
        if i<6:spec['Điện áp lựa chọn']='AC 6,12,24,36,48,110,220,380V; DC 6,12,24,36,48,110,220V'
        else:spec['Phù hợp']=r[2]
        add(6, 1, i, 5, r[4], 'RELAY' if i<6 else 'ACCESSORY', 'Rơ le trung gian' if i<6 else 'Đế rơ le', spec)
    for i in (4,5,6,7):
        r = tables[7][0][i]
        add(7, 0, i, 5, r[4], 'TIMER', 'Rơ le thời gian', {'In':'3A' if i==7 else '5A', 'Chức năng':r[2]})
    for i in (2,3,4,5,8,9,10):
        r = tables[7][1][i]
        add(7, 1, i, 6, r[4], 'PHASE_RELAY' if i<6 else 'MOTOR_PROTECTION',
            'Rơ le bảo vệ pha' if i<6 else 'Rơ le bảo vệ động cơ',
            {'Chức năng' if i<6 else 'Dải dòng (A)':r[2]})
    current = None
    for i, r in enumerate(tables[8][0][3:], 3):
        current = r[0] or current
        poles = '3P' if '/3B' in r[2] else '4P'
        add(8, 0, i, 3 if poles=='3P' else 4, r[2], 'ATS', 'NXZM', {'In (A)':current, 'Số cực':poles})
    for i, r in enumerate(tables[8][1][2:], 2):
        add(8, 1, i, 4, r[3], 'SOFT_STARTER', 'NJR2', {'Công suất':r[0], 'In':r[2], 'Điện áp':'380V (±15%)', 'Bypass':'Không tích hợp'})
    for i, r in enumerate(tables[9][0][3:], 3):
        add(9, 0, i, 8, r[6], 'TRANSFORMER', 'NDK', {'Công suất':r[0], 'Vật liệu dây':'Nhôm', 'Điện áp vào/ra lựa chọn':'415 380 220 / 220 110 48 24 12V'})
    for i in (2,6,7):
        r = tables[10][0][i]
        add(10, 0, i, 11, r[8], 'LIGHT' if i==2 else 'ACCESSORY', 'Đèn báo' if i==2 else 'Ổ cắm cài rail',
            {'Màu sắc' if i==2 else 'In/Ue':r[0], 'Điện áp' if i==2 else 'Chân cắm':r[3]})
    for i in (10,14,18,22,26,30,31):
        r = tables[10][0][i]
        category = 'PUSHBUTTON' if i<22 else 'SELECTOR_SWITCH' if i<30 else 'FUSE'
        spec = {'Màu sắc' if i<22 else 'Chức năng' if i<30 else 'Loại':r[0],
                'Tiếp điểm' if i<30 else 'Dòng định mức ruột chì':r[2]}
        if i<30:spec['Vật liệu']=r[6]
        if i in (22,26):spec['Số vị trí']='2' if i==22 else '3'
        add(10, 0, i, 11, r[9], category, 'Nút nhấn' if i<22 else 'Chuyển mạch' if i<30 else 'Cầu chì', spec)
    for i, r in enumerate(tables[11][1][4:], 4):
        add(11, 1, i, 9, r[6], 'CONTACTOR', 'NCH8', {'In (A)':r[0], 'Số cực':'2P', 'Tiếp điểm':'2NO'})

    # Independent page-text accounting catches dropped or duplicated price cells.
    source_counts = {}
    for page_no, page in enumerate(doc, 1):
        # Price columns are right of x=310pt in this reviewed layout. Left-side
        # current lists such as "80,100" are not monetary values.
        expected = Counter(int(w[4].replace(',', '')) for w in page.get_text('words')
                           if w[0] >= 310 and MONEY.fullmatch(w[4]))
        actual = Counter(r['price'] for r in rows if r['source_page']==page_no)
        if expected != actual:
            raise ValueError(f'Page {page_no} prices disagree: missing={expected-actual}, extra={actual-expected}')
        source_counts[page_no] = sum(expected.values())
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate source identities')
    return rows, source_counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace-brand', action='store_true',
                        help='Replace all CHINT pricebook, web-offer and catalog-feed rows with this book.')
    args = parser.parse_args()
    rows, page_counts = extract(args.source)
    report_dir = ROOT/'docs/chint-dika-update-2026-10-26'
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {'source_sha256':SOURCE_SHA, 'numeric_price_rows':len(rows),
              'per_page':page_counts, 'vat_status':'excluded', 'discount_applied_percent':0,
              'policy':'Keep other supplier books and all reviewed CAD links; import distinct source offers without guessing exact order configurations.',
              'applied':args.apply}
    if args.apply:
        target = ROOT/'app/data/supplier_pricebooks.json'
        before = target.read_bytes()
        payload = json.loads(before)
        backup = report_dir/'supplier_pricebooks.before.json'
        if not backup.exists():backup.write_bytes(before)
        if args.replace_brand:
            from app.services.ai.manufacturer_registry import canonical_brand
            is_chint = lambda r: canonical_brand(r.get('brand')) == 'CHINT'
            reset_dir = report_dir / ('reset-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
            reset_dir.mkdir()
            (reset_dir / target.name).write_bytes(before)
            unrelated = [r for r in payload['items'] if not is_chint(r)]
            report['removed_supplier_rows'] = len(payload['items']) - len(unrelated)
            report['removed_other_feed_rows'] = {}
            for filename in ('web_catalog_offers.json', 'external_product_information.json', 'catalog_documents.json'):
                path = target.parent / filename
                original = path.read_bytes()
                content = json.loads(original)
                retained = [r for r in content['items'] if not is_chint(r)]
                report['removed_other_feed_rows'][filename] = len(content['items']) - len(retained)
                (reset_dir / filename).write_bytes(original)
                content['items'] = list(retained)
                if filename == 'catalog_documents.json':
                    content['items'].append({'brand':'CHINT', 'title':'Bảng giá CHINT T6-2026',
                        'url':'/device-catalog/documents/' + SOURCE_KEY, 'source_label':'DIKA',
                        'checked_at':rows[0]['checked_at'], 'effective_date':None,
                        'status':'source_document', 'verified_pages':11})
                staged = path.with_suffix('.json.tmp')
                staged.write_text(json.dumps(content,ensure_ascii=False,indent=2),encoding='utf-8')
                staged.replace(path)
                assert [r for r in json.loads(path.read_text(encoding='utf-8'))['items'] if not is_chint(r)] == retained
            report['policy'] = 'Replace all CHINT pricebook feed sources with the supplied PDF; preserve other brands and equipment/CAD library.'
            report['backup_directory'] = str(reset_dir)
        else:
            unrelated = [r for r in payload['items'] if not r['id'].startswith(SOURCE_KEY+':')]
        payload['items'] = unrelated + rows
        models = {}
        for r in payload['items']:
            if r.get('brand')=='CHINT':models.setdefault(r['item_name'], []).append(r['id'])
        payload['manufacturers']['CHINT']['models'] = models
        source_copy = ROOT/'storage/catalog-pricebooks'/f'{SOURCE_KEY}.pdf'
        source_copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(args.source, source_copy)
        staging = target.with_suffix('.json.tmp')
        staging.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        staging.replace(target)
        # Preserve the exact pre-existing rows, including other brands and CAD data.
        persisted = json.loads(target.read_text(encoding='utf-8'))
        assert [r for r in persisted['items'] if not r['id'].startswith(SOURCE_KEY+':')] == unrelated
        report['preserved_existing_rows'] = len(unrelated)
        report['total_chint_rows'] = sum(r.get('brand')=='CHINT' for r in persisted['items'])
    (report_dir/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()

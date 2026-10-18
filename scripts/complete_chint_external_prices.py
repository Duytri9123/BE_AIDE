"""Publish reviewed CHINT seller prices and browsing choices in both catalogs.

Seller prices are separate from the 2026 manufacturer pricebook. Component
offers never become a price for an entire assembly or a CAD insertion approval.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from scripts.refresh_ple_prices import parse_card

ROOT = Path(__file__).resolve().parents[1]
PLE = 'https://www.ple.vn/manufacturer/chint/by%2Cproduct_name/results%2C1-1000.html?keyword=&lang=en&language=en-GB'
FUSE_URL = 'https://shopee.vn/Cầu-chì-Chint-RT36-00-(NT00)-gG-160A-i.400687483.22018556065'
BASE_URL = 'https://baoanjsc.com.vn/san-pham/de-cau-chi-chint-base-rt36-00-series-BASE-RT36-00_839667_vn.aspx'


def ats_rows(html, checked):
    rows = []
    for card in BeautifulSoup(html, 'html.parser').select('.product-container'):
        row = parse_card(card, 'CHINT', 'Chint', PLE, checked)
        if not row:
            continue
        match = re.fullmatch(r'ATS Chint (NZ7-125([HS])/([34])) (25|32|40|50|63|80|100)A', row['name'], re.I)
        if not match:
            continue
        row['sku'] = match[1]+' '+match[4]+'A'
        row['category'] = 'ATS'
        row['specifications'].update({'Số cực':match[3]+'P', 'In (A)':match[4],
                                      'Họ thiết bị':'NZ7-125'})
        rows.append(row)
    return rows


def component_rows(checked):
    rows = []
    # Public seller pages inspected 2026-10-16 through web search/open.
    # Keep the source excerpt: a later import must not silently invent a price.
    for sku, kind, price, url, seller, scope, availability, excerpt in [
        ('RT36-00 (NT00) gG 160A', 'FUSE', 170000, FUSE_URL, 'BluePower Automation · Shopee',
         'Ruột cầu chì; chưa gồm đế', 'Hàng đặt trước; không có sẵn',
         '(ORDER - KHÔNG CÓ SẴN) Cầu chì Chint RT36-00 (NT00) gG 160A · 170.000₫'),
        ('BASE RT36-00', 'FUSE_HOLDER', 69100, BASE_URL, 'Bảo An Automation',
         'Đế cầu chì 1P; mua ruột riêng', 'Cần xác nhận tồn kho',
         'Đế cầu chì CHINT BASE RT36-00 · 69,100₫ · 1P · Tùy chọn (Mua riêng) RT36-00 160A gG'),
    ]:
        spec = {'Phạm vi giá':scope, 'Tình trạng':availability, 'VAT':'Chưa xác nhận'}
        if kind == 'FUSE':
            spec.update({'In (A)':'160', 'Họ thiết bị':'RT36-00', 'Cấp sử dụng':'gG'})
        else:
            spec.update({'Số cực':'1P', 'Dùng cho':'RT36-00'})
        rows.append(dict(id='web:'+hashlib.sha1(url.encode()).hexdigest()[:16], sku=sku,
                         name=sku, brand='CHINT', category=kind, price=price, currency='VND',
                         source_url=url, source_label=seller, source_kind='web_seller',
                         checked_at=checked, source_excerpt=excerpt,
                         source_observation='Public web indexed page reviewed 2026-10-16; confirm current quotation',
                         vat_status='unknown', specifications=spec,
                         columns=['Tên hàng','Phạm vi giá','Tình trạng','VAT','Đơn giá'],
                         cells=[sku,scope,availability,'Chưa xác nhận',f'{price:,}'],
                         price_note='Giá tham khảo từng bộ phận tại nguồn công khai; chưa phải giá cả bộ. Xác nhận VAT và giá hiện hành.'))
    return rows


def main():
    checked = datetime.now(timezone.utc).isoformat()
    response = httpx.get(PLE, follow_redirects=True, timeout=40)
    response.raise_for_status()
    offers = ats_rows(response.text, checked)
    if len(offers) != 21:
        raise ValueError(f'Expected 21 reviewed NZ7-125 variants, got {len(offers)}; inspect seller changes')
    offers += component_rows(checked)
    web_path = ROOT/'app/data/web_catalog_offers.json'
    web = json.loads(web_path.read_text(encoding='utf8'))
    merged = {r['id']:r for r in web['items']}
    for row in offers:
        merged[row['id']] = row
    web['items'] = list(merged.values())

    book_path = ROOT/'app/data/supplier_pricebooks.json'
    book = json.loads(book_path.read_text(encoding='utf8'))
    repaired = []
    for row in book['items']:
        if row.get('brand') != 'CHINT':
            continue
        sku = row.get('sku', '')
        if sku.startswith('NCH8-'):
            row['category'] = 'CONTACTOR'
            row['group'] = 'NCH8 · CONTACTOR'
            row['specifications']['Họ thiết bị'] = sku.split('/')[0]
            row['specifications']['In (A)'] = row['specifications']['In'].removesuffix('A')
            repaired.append(row['id'])
        elif re.fullmatch(r'NP2-E[DJG]\d+', sku):
            row['category'] = 'SELECTOR_SWITCH'
            row['group'] = 'NP2 · SELECTOR_SWITCH'
            row['specifications']['Họ thiết bị'] = 'NP2'
            repaired.append(row['id'])

    option_path = ROOT/'app/data/library_price_options.json'
    options = json.loads(option_path.read_text(encoding='utf8'))
    option_map = {r['price_row_id']:r for r in options['options']}
    def option(row, equipment, evidence):
        option_map[row['id']] = dict(price_row_id=row['id'], equipment_catalog_id=equipment,
            status='configuration_option', model=row['sku'], identity_evidence=evidence,
            cad_insertion_verified=False)
    for row in offers:
        if row['category'] == 'ATS' and row['specifications']['Số cực'] == '4P':
            option(row, 'TB-e62130601b4d5568', 'CHINT NZ7-125 CAD is 4P; seller specifies NZ7-125H/4 with separate rated-current variants. Select subtype and current; no geometry approval.')
        elif row['category'] in {'FUSE', 'FUSE_HOLDER'}:
            option(row, 'TB-23fd57135f41bb9f', 'RT36-00 CAD contains fuse and base; this offer prices only the explicitly named component, never the entire assembly.')
    for row in book['items']:
        if row.get('brand') != 'CHINT':
            continue
        sku = row.get('sku','')
        if re.fullmatch(r'NCH8-(20|25)/(20|11|02) 220/230V', sku):
            option(row, 'TB-f23727fc64d7aabb', '2026 PDF page 25: NCH8-20/25 modular contactor, 2 main contacts; 2NO, 1NO+1NC or 2NC variants. CAD is shared family reference; select coil and contacts.')
        elif re.fullmatch(r'NP2-E[DJG]\d+', sku):
            option(row, 'TB-9ae0c2b23bf4de77', '2026 PDF pages 62-63 specify NP2 rotary selectors; CAD identifies NP2 selector only. Choose positions, return action and contacts separately.')
    options['options'] = list(option_map.values())
    for path, data in [(web_path,web), (book_path,book), (option_path,options)]:
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'seller_rows':len(offers),'repaired_rows':len(repaired)},ensure_ascii=False))


if __name__ == '__main__':
    main()

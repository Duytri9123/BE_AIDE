"""Import reviewed exact drive SKUs from 07/2026, preserving PDF columns.

Contact-for-price entries are never converted to zero-price offers. ATV320 B/C
and ATV212 H/W remain different models even when the motor power is the same.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.se.com/vn/vi/download/document/MasterPriceBook/'
PREFIX = 'schneider-2026-drives:'


def page_offers(words, page):
    for w in words:
        sku = w[4]
        if not re.fullmatch(r'ATV(?:320(?:U\d{2}|D\d{2})(?:M2|M3|N4)[BC]|212[HW](?:075|U\d{2}|D\d{2})N4|630(?:U\d{2}|D\d{2}|C\d{2})N4(?:\(5\))?)',sku):
            continue
        if page == 189:
            if 220<w[0]<300:
                prices = [p for p in words if 325<p[0]<380]
            elif 385<w[0]<465:
                prices = [p for p in words if 490<p[0]<545]
            else:
                continue  # product photo caption
        elif 390<w[0]<475:
            prices = [p for p in words if 490<p[0]<550]
        else:
            continue
        prices = [p for p in prices if abs(p[1]-w[1])<1.5 and re.fullmatch(r'\d{1,3}(?:\.\d{3})+',p[4])]
        if not prices:
            if page == 191 and 'C' in sku[6:]:
                continue  # C11 and higher explicitly Contact for price
            raise ValueError('Missing exact price cell '+sku)
        if len(prices)!=1:
            raise ValueError('Ambiguous price column '+sku)
        yield sku.removesuffix('(5)'), int(prices[0][4].replace('.',''))


def extract(path):
    doc = pymupdf.open(path)
    if len(doc)!=282:
        raise ValueError('Expected reviewed 282-page pricebook')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = []
    for page in (185,186,189,191):
        for sku, price in page_offers(doc[page-1].get_text('words'),page):
            family = sku[:6]
            spec = {'Họ thiết bị':sku, 'Dòng sản phẩm':family}
            if family == 'ATV320':
                spec['Kiểu thân'] = 'Compact (C)' if sku.endswith('C') else 'Book (B)'
            elif family == 'ATV212':
                spec['Cấp bảo vệ'] = 'IP21' if sku[6]=='H' else 'IP55'
            spec['Mã đặt hàng'] = sku
            rows.append({'id':PREFIX+sku,'sku':sku,'item_name':sku,'name':sku,
                'brand':'Schneider Electric','category':'VFD','group':'Biến tần · '+family,
                'price':price,'currency':'VND','specifications':spec,
                'columns':['Tên hàng','Mã đặt hàng','Thông tin','Giá bán'],
                'cells':[sku,sku,' · '.join(f'{k}: {v}' for k,v in spec.items()),f'{price:,}'.replace(',','.')],
                'source_label':'Schneider Việt Nam 07/2026','source_url':SOURCE,
                'source_kind':'supplier_pricebook','source_page':page,'source_sha256':sha,
                'checked_at':datetime.now(timezone.utc).isoformat(),'edition':'07/2026','vat_status':'included',
                'price_note':'Giá niêm yết gồm VAT. Giữ đúng hậu tố thân/điện áp; chọn mã cụ thể trước khi bóc tách.'})
    if len({r['sku'] for r in rows})!=len(rows):
        raise ValueError('Duplicate drive SKU')
    return rows


if __name__=='__main__':
    rows = extract(ROOT/'tmp/folder-web-review/schneider-2026.pdf')
    if len(rows)!=98:
        raise ValueError('Reviewed page counts changed; inspect before publication')
    path = ROOT/'app/data/supplier_pricebooks.json'
    data = json.loads(path.read_text(encoding='utf8'))
    data['items'] = [r for r in data['items'] if not r['id'].startswith(PREFIX)] + rows
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Reviewed exact drive prices:',len(rows))

"""Import seller offers with an explicit manufacturer, product code and VND price."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {'Hager': 2, 'Legrand': 3, 'Siemens': 29}


def parse_card(card, brand, collection, checked):
    description = card.select_one('[itemprop=description]')
    title = card.select_one('[itemprop=name][href]')
    amount = card.select_one('[itemprop=price]')
    currency = card.select_one('[itemprop=priceCurrency]')
    if not all((description, title, amount, currency)) or currency.get_text(strip=True) != 'VND':
        return None
    text = description.get_text('\n', strip=True)
    if not re.search(r'Thương hiệu:\s*'+re.escape(brand)+r'(?:\s|$)', text, re.I):
        return None
    code = re.search(r'Mã sản phẩm:\s*([A-Z0-9./-]+)', text, re.I)
    value = amount.get_text(strip=True)
    if not code or not re.fullmatch(r'\d+(?:\.0+)?', value) or float(value) <= 0:
        return None
    name = title.get_text(' ', strip=True)
    kind = next((k for k in ('RCBO', 'RCCB', 'MCCB', 'MCB', 'ACB') if re.search(r'\b'+k+r'\b', name)), 'ACCESSORY')
    spec = {}
    poles = re.search(r'Số cực:\s*([1-4])(?:P)?\b', text, re.I)
    current = re.search(r'Dòng (?:điện )?định mức(?: In \(A\))?:\s*(\d+(?:[.,]\d+)?)\s*A\b', text, re.I)
    if poles:
        spec['Số cực'] = poles[1]+'P'
    if current:
        spec['In (A)'] = current[1]
    url = urljoin(collection, title['href'])
    if urlparse(url).hostname != 'www.makel.vn':
        return None
    return dict(id='web:'+hashlib.sha1(url.encode()).hexdigest()[:16], sku=code[1], name=name,
                brand=brand, category=kind, price=int(float(value)), currency='VND',
                specifications=spec, source_url=url, collection_url=collection,
                source_kind='web_seller', source_label='Makel', checked_at=checked,
                price_note='Giá bán VND theo Offer của nhà bán hàng; VAT và tồn kho cần xác nhận.')


def refresh():
    checked = datetime.now(timezone.utc).isoformat()
    rows, reviews = [], []
    for brand, identity in SOURCES.items():
        url = f'https://www.makel.vn/thiet-bi-dong-cat-chong-dong-ro?brand={identity}'
        response = httpx.get(url, timeout=35, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        accepted = [r for card in soup.select('.oe_product')
                    if (r := parse_card(card, brand, url, checked))]
        rows.extend(accepted)
        reviews.append(dict(brand=brand, url=url, accepted_rows=len(accepted), checked_at=checked,
                            scope='First switching equipment manufacturer page', status='checked'))
        print(brand, len(accepted), flush=True)
    path = ROOT/'app/data/web_catalog_offers.json'
    payload = json.loads(path.read_text(encoding='utf8'))
    reviewed = {r['url'] for r in reviews}
    merged = {r['source_url']: r for r in payload['items']
              if not (r.get('source_label') == 'Makel' and r.get('collection_url') in reviewed)}
    for row in rows:
        merged[row['source_url']] = row
    payload['items'] = list(merged.values())
    payload['makel_source_review'] = reviews
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__':
    refresh()

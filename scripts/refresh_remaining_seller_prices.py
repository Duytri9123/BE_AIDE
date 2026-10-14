"""Import explicit Morele and Delta seller prices, without quote-only products."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup


def refresh():
    rows = []
    checked = datetime.now(timezone.utc).isoformat()

    def add(brand, code, name, category, price, url, collection):
        rows.append(dict(id='web:'+hashlib.sha1((url+'#'+code).encode()).hexdigest()[:16], sku=code,
                         name=name, brand=brand, category=category, price=price, currency='VND',
                         source_url=url+'#'+code, collection_url=collection, source_kind='web_seller',
                         source_label='Hạnh Dũng' if brand == 'Morele' else 'Cơ Điện Hải Âu',
                         checked_at=checked, specifications={},
                         price_note='Giá bán niêm yết tại lần kiểm tra; VAT và cấu hình cần xác nhận.'))

    url = 'https://hanhdungelectric.com.vn/quat-lam-mat-huong-truc-morele'
    response = httpx.get(url, follow_redirects=True, timeout=35)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text(' ', strip=True)
    for code, amount in re.findall(r'\d\. Morele (\d{5}HSL) Giá bán: (\d{1,3}(?:\.\d{3})+) VNĐ', text):
        add('Morele', code, 'Quạt Morele '+code, 'FAN', int(amount.replace('.', '')), url, url)
    for card in soup.select('.product-box'):
        title, price = card.select_one('h3 a[href]'), card.select_one('.price-box')
        if not title or not price:
            continue
        name = title.get_text(' ', strip=True)
        amount = price.get_text(' ', strip=True)
        code = re.search(r'\bMORELE\s+([A-Z0-9/-]+)\b', name, re.I)
        if not code or not re.fullmatch(r'\d{1,3}(?:\.\d{3})+₫', amount):
            continue
        kind = 'SELECTOR_SWITCH' if 'XOAY' in name else 'AUX_CONTACT' if 'TIẾP ĐIỂM' in name else 'PUSHBUTTON'
        add('Morele', code[1], name, kind, int(re.sub(r'\D', '', amount)), urljoin(url, title['href']), url)

    url = 'https://codienhaiau.com/brand/delta/'
    response = httpx.get(url, follow_redirects=True, timeout=35)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for card in soup.select('li.product'):
        title, link = card.select_one('h2,h3'), card.select_one('a.woocommerce-LoopProduct-link[href]')
        prices = [p for p in card.select('.price bdi') if not p.find_parent('del')]
        if not title or not link or len(prices) != 1:
            continue
        name = title.get_text(' ', strip=True)
        model = re.search(r'\bDelta\s+([A-Z0-9-]+)\b', name, re.I)
        amount = prices[0].get_text(' ', strip=True)
        if not model or not re.search(r'\d', model[1]) or not re.fullmatch(r'\d{1,3}(?:\.\d{3})+\s*₫', amount):
            continue
        kind = 'HMI' if 'HMI' in name else 'PLC' if model[1].startswith('DVP') else 'INVERTER' if 'biến tần' in name.lower() else 'ACCESSORY'
        add('Delta', model[1], name, kind, int(re.sub(r'\D', '', amount)), link['href'], url)
    path = Path(__file__).resolve().parents[1]/'app/data/web_catalog_offers.json'
    data = json.loads(path.read_text(encoding='utf8'))
    merged = {r['source_url']: r for r in data['items']}
    for row in rows:
        merged[row['source_url']] = row
    data['items'] = list(merged.values())
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print({b: sum(r['brand'] == b for r in rows) for b in ('Morele', 'Delta')})


if __name__ == '__main__':
    refresh()

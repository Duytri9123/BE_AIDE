"""Review requested makers from the seller's own manufacturer navigation."""
import asyncio
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.customer_manufacturers import CUSTOMER_MANUFACTURERS

INDEX = 'https://www.ple.vn/manufacturer/delixi/by%2Cmf_name/results%2C1-180.html?keyword=&lang=vi&language=vi-VN'


def parse_card(card, brand, source_label, collection, checked):
    title = card.select_one('h2 a[href]')
    prices = card.select('.product-price span.PricesalesPrice')
    if not title or len(prices) != 1:
        return None
    amount = prices[0].get_text(' ', strip=True)
    if not re.fullmatch(r'\d{1,3}(?:,\d{3})+\s*₫', amount):
        return None
    name = title.get_text(' ', strip=True)
    maker = re.search(re.escape(source_label), name, re.I)
    if not maker:
        return None
    tail = name[maker.end():].strip()
    codes = [t.strip(',|()') for t in tail.split()]
    codes = [t for t in codes if re.fullmatch(r'[A-Za-z0-9._/-]+', t)
             and re.search(r'\d', t) and (re.search(r'[A-Za-z]', t) or re.fullmatch(r'\d{5,12}', t))
             and not re.fullmatch(r'(?:AC|DC)?\d+(?:[.,]\d+)?(?:/\d+)?(?:P|A|mA|V|VAC|VDC|kA|kW|kVA|kVAR|Hz|uF|nF)', t, re.I)]
    if not codes:
        return None
    sku = codes[0]
    if brand == 'EMIC':
        model = re.search(r'\b(?:EM\dH\d+[A-Z]?|CV\d+[A-Z]?|CE\d+[A-Z]?|VA\d+)\b', tail, re.I)
        if not model:
            return None
        sku = model[0]
    kind = next((kind for pattern, kind in [
        (r'\bRCBO\b', 'RCBO'), (r'\bRCCB\b', 'RCCB'), (r'\bMCCB\b', 'MCCB'),
        (r'\bMCB\b', 'MCB'), (r'\bACB\b', 'ACB'),
        (r'khởi động từ|contactor', 'CONTACTOR'), (r'rơ le nhiệt|relay nhiệt', 'THERMAL_RELAY'),
        (r'bộ điều khiển tụ bù', 'POWER_FACTOR_CONTROLLER'),
        (r'biến tần', 'INVERTER'), (r'biến dòng', 'CT'), (r'cầu đấu', 'TERMINAL_BLOCK'),
        (r'tụ bù', 'CAPACITOR'), (r'đèn báo', 'LIGHT'), (r'nút nhấn', 'PUSHBUTTON'),
        (r'đồng hồ|công tơ', 'METER'), (r'rơ le|relay', 'RELAY')]
        if re.search(pattern, name, re.I)), 'ACCESSORY')
    spec = {}
    for label, pattern in [('Số cực', r'\b[1-4]P\b'), ('In (A)', r'\b(\d+(?:[.,]\d+)?)\s*A\b'),
                           ('Điện áp', r'\b\d+(?:[.,]\d+)?\s*(?:V|VAC|VDC)\b'),
                           ('Khả năng cắt và điện áp', r'\b\d+(?:[.,]\d+)?\s*kA\b')]:
        match = re.search(pattern, name, re.I)
        if match:
            spec[label] = match[1] if label == 'In (A)' else match[0]
    ratio = re.search(r'\b(\d+)\s*/\s*(\d+)\s*A\b', name, re.I)
    if kind == 'CT' and ratio:
        spec['In (A)'], spec['Dòng thứ cấp (A)'] = ratio[1], ratio[2]
        sku += ' '+ratio[1]+'/'+ratio[2]+'A'
    url = urljoin(collection, title['href'])
    if urlparse(url).hostname != 'www.ple.vn':
        return None
    return dict(id='web:'+hashlib.sha1(url.encode()).hexdigest()[:16], sku=sku, name=name,
                brand=brand, category=kind, price=int(re.sub(r'\D', '', amount)), currency='VND',
                source_url=url, collection_url=collection, source_label='PLE', source_kind='web_seller',
                checked_at=checked, specifications=spec,
                price_note='Giá bán niêm yết tại lần kiểm tra; VAT và tồn kho cần xác nhận, không phải bảng giá hãng.')


async def refresh():
    checked = datetime.now(timezone.utc).isoformat()
    rows, reviews = [], []
    async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
        response = await client.get(INDEX)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        sources = {'Delixi': ('Delixi', INDEX), 'SK': ('SK', 'https://www.ple.vn/manufacturer/sk/dirDesc/results%2C21-920.html?keyword=&lang=vi&language=vi-VN')}
        for a in soup.select('a[href]'):
            if '/manufacturer/' not in a['href']:
                continue
            title = a.get_text(' ', strip=True)
            brand = canonical_brand(title)
            if brand not in CUSTOMER_MANUFACTURERS:
                continue
            url = urljoin(INDEX, a['href'])
            if urlparse(url).hostname == 'www.ple.vn':
                sources.setdefault(brand, (title, url))
        sem = asyncio.Semaphore(3)

        async def read(brand, source):
            title, url = source
            async with sem:
                try:
                    result = await client.get(url)
                    result.raise_for_status()
                    if urlparse(str(result.url)).hostname != 'www.ple.vn':
                        raise ValueError('Unexpected seller redirect')
                    page = BeautifulSoup(result.text, 'html.parser')
                    accepted = [r for card in page.select('.product-container')
                                if (r := parse_card(card, brand, title, url, checked))]
                    rows.extend(accepted)
                    reviews.append(dict(brand=brand, url=url, accepted_rows=len(accepted), checked_at=checked,
                                        scope='First manufacturer page, up to 180 products', status='checked'))
                    print(brand, len(accepted), flush=True)
                except Exception as exc:
                    reviews.append(dict(brand=brand, url=url, accepted_rows=0, checked_at=checked,
                                        status='fetch_failed', error=type(exc).__name__))
        await asyncio.gather(*(read(brand, source) for brand, source in sources.items()))
    path = ROOT/'app/data/web_catalog_offers.json'
    payload = json.loads(path.read_text(encoding='utf8'))
    checked_urls = {r['url'] for r in reviews if r['status'] == 'checked'}
    merged = {r['source_url']: r for r in payload['items']
              if not (r.get('source_label') == 'PLE' and r.get('collection_url') in checked_urls)}
    for row in rows:
        merged[row['source_url']] = row
    payload['items'] = list(merged.values())
    payload['ple_source_review'] = reviews
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('Total accepted', len(rows), 'manufacturers reviewed', len(reviews))


if __name__ == '__main__':
    asyncio.run(refresh())

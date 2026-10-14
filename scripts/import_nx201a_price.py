"""Add the exact legacy NX201A price; never alias it to N201/R201."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://codienhaiau.com/category/mikro/ro-le-mikro/'


def import_price(html):
    soup = BeautifulSoup(html, 'html.parser')
    cards = [h for h in soup.select('h2.woocommerce-loop-product__title') if 'NX201A-240A' in h.get_text()]
    if len(cards) != 1:
        raise ValueError('Expected one exact NX201A-240A product')
    card = cards[0].find_parent('li')
    prices = card.select('.price .woocommerce-Price-amount')
    if len(prices) != 1:
        raise ValueError('Missing or ambiguous price; preserve existing prices')
    text = prices[0].get_text(' ', strip=True)
    if not re.fullmatch(r'\d{1,3}(?:\.\d{3})+\s*₫', text):
        raise ValueError('Expected explicit VND amount')
    url = card.select_one('a.woocommerce-LoopProduct-link')['href']
    if not url.startswith('https://codienhaiau.com/product/'):
        raise ValueError('Unexpected seller URL')
    row = dict(id='web:'+hashlib.sha1(url.encode()).hexdigest()[:16], sku='NX201A-240A',
        name=cards[0].get_text(' ',strip=True), brand='Mikro', category='EARTH_FAULT_RELAY',
        price=int(re.sub(r'\D','',text)), currency='VND', source_url=url,
        collection_url=SOURCE, source_label='Cơ điện Hải Âu', source_kind='web_seller',
        checked_at=datetime.now(timezone.utc).isoformat(),
        specifications={'Điện áp phụ trợ':'198–265 V AC', 'Tần số':'50 Hz', 'Dải chỉnh định':'0.1–2 A'},
        manufacturer_document='https://itmikro.com.my/nx201a-earth-fault-relay/',
        price_note='Giá bán nhà cung cấp tại lần kiểm tra; VAT, tồn kho và tình trạng dòng cũ cần xác nhận. Không thay bằng N201/R201.')
    path=ROOT/'app/data/web_catalog_offers.json'
    payload=json.loads(path.read_text(encoding='utf8'))
    merged={r['source_url']:r for r in payload['items']}
    merged[url]=row
    payload['items']=list(merged.values())
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(row['sku'],row['price'])


if __name__=='__main__':
    import_price(Path(sys.argv[1]).read_text(encoding='utf8'))

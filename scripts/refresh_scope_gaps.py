"""Review explicitly named SK, Sino-Vanlock and Andeli seller prices."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def sino_rows(soup):
    rows = []
    for table in soup.select('table'):
        for tr in table.select('tr'):
            cells = [c.get_text(' ', strip=True) for c in tr.select('td')]
            if len(cells) != 4 or not re.fullmatch(r'\d+', cells[0]) or not re.fullmatch(r'\d{1,3}(?:\.\d{3})+', cells[3]):
                continue
            code = re.search(r'\b((?:PS|SC)\d+[A-Z]+\s*/C\d+)\b', cells[1])
            poles = re.search(r'\b([1-4])P\b', cells[1])
            current = re.search(r'\b(\d+)A\b', cells[1])
            if code and poles and current:
                rows.append((re.sub(r'\s+', '', code[1]), cells[1], int(cells[3].replace('.', '')),
                             {'Số cực': poles[1]+'P', 'In (A)': current[1]}))
    grouped = {}
    for row in rows:
        grouped.setdefault(row[0], []).append(row)
    # A source typo reuses SC45N/C3006 for 3P and 4P. Neither row is
    # an approved identity until the seller corrects that conflict.
    return [group[0] for group in grouped.values() if all(r == group[0] for r in group)]


def refresh():
    rows = []
    checked = datetime.now(timezone.utc).isoformat()

    def add(brand, code, name, kind, price, url, collection, spec=None, note=None):
        rows.append(dict(id='web:'+hashlib.sha1((url+'#'+code).encode()).hexdigest()[:16], sku=code,
                         name=name, brand=brand, category=kind, price=price, currency='VND',
                         source_url=url+'#'+code, collection_url=collection,
                         source_kind='web_seller', source_label={'SK':'Điện Hòa Phú','Sino - Vanlock':'Điện Nước Hà Nội','Andeli':'Vật liệu điện VH','Danfoss':'Eriko'}[brand],
                         checked_at=checked, specifications=spec or {},
                         price_note=note or 'Giá bán niêm yết tại lần kiểm tra; VAT và tồn kho cần xác nhận.'))

    url = 'https://dienhoaphu.vn/danh-muc-san-pham/thiet-bi-dien-cong-nghiep/tu-bu-bo-dieu-khien-tu-bu-cuon-khang/bo-dieu-khien-tu-bu/sk/'
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for card in soup.select('li.product'):
        title, link = card.select_one('h2'), card.select_one('a.woocommerce-LoopProduct-link[href]')
        prices = [p for p in card.select('.price bdi') if not p.find_parent('del')]
        if not title or not link or len(prices) != 1:
            continue
        name = title.get_text(' ', strip=True)
        code = re.search(r'\bSK (QR-X\d+)\b', name)
        amount = prices[0].get_text(' ', strip=True)
        if code and re.fullmatch(r'₫\s*\d{1,3}(?:,\d{3})+', amount):
            add('SK', code[1], name, 'POWER_FACTOR_CONTROLLER', int(re.sub(r'\D','',amount)), link['href'], url)

    url = 'https://thietbidiennuochanoi.vn/pages/bang-gia-aptomat-sino-vanlock'
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    assert 'Sino' in soup.get_text() and 'Vanlock' in soup.get_text()
    for code, name, price, spec in sino_rows(soup):
        add('Sino - Vanlock', code, name, 'MCB', price, url, url, spec)

    url = 'https://vanvh.com/den-bao-pha-cac-loai/den-bao-do-vang-xanh-phi-22-andeli-andeli-ad16-22ds'
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text(' ', strip=True)
    name = soup.select_one('h1').get_text(' ',strip=True)
    code = re.search(r'Hãng sản xuất\s*:\s*ANDELI Model\s*:\s*([A-Z0-9-]+)', text)
    amount = re.search(r'Giá bán:\s*(\d{1,3}(?:,\d{3})+) đ\s*\( Giá chưa VAT \)', text)
    if code and amount and 'ANDELI' in name:
        add('Andeli', code[1], name, 'LIGHT', int(amount[1].replace(',','')), url, url,
            note='Giá bán chưa VAT; cần chọn màu và điện áp theo đơn hàng, chưa xác nhận cấu hình CAD.')
    url = 'https://eriko.com.vn/san-pham/3332-bang-gia-cam-bien-do-ap-suat.html'
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for tr in soup.select('table tr'):
        cells = [c.get_text(' ',strip=True) for c in tr.select('td')]
        if len(cells) != 3 or cells[1] != 'Danfoss' or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',cells[2]):
            continue
        model = re.fullmatch(r'MBS3000\((060G\d+)\)\s*\((0-[\d.]+bar)\)', cells[0], re.I)
        if model:
            add('Danfoss', model[1], cells[0], 'PRESSURE_SENSOR', int(cells[2].replace(',','')), url, url,
                {'Dải áp suất': model[2]}, 'Giá tham khảo do Eriko công bố; VAT, ngày hiệu lực và tồn kho cần xác nhận.')
    path = ROOT/'app/data/web_catalog_offers.json'
    data = json.loads(path.read_text(encoding='utf8'))
    reviewed = {r['collection_url'] for r in rows}
    merged = {r['source_url']:r for r in data['items'] if r.get('collection_url') not in reviewed}
    for row in rows:
        merged[row['source_url']] = row
    data['items'] = list(merged.values())
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print({brand:sum(r['brand']==brand for r in rows) for brand in ('SK','Sino - Vanlock','Andeli','Danfoss')})


if __name__ == '__main__':
    refresh()

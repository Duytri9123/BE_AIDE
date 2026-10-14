"""Import explicit MITEX CT configurations from a saved seller page."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from scripts.refresh_ple_prices import parse_card

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.ple.vn/manufacturer/mitex/by,product_name.html?lang=vi&language=vi-VN'


def parse_ct(card, checked):
    row = parse_card(card, 'MITEX', 'Mitex', SOURCE, checked)
    if not row:
        return None
    name = row['name']
    model = re.search(r'\b(BD0[123])\s+CCX\s+(\d+(?:[.,]\d+)?)', name, re.I)
    ratio = re.search(r'tỷ số\s+(\d+)/(\d+)A', name, re.I)
    burden = re.search(r'(\d+(?:[.,]\d+)?)\s*VA', name, re.I)
    turns = re.search(r'W\s*=\s*(\d+)', name, re.I)
    opening = re.search(r'(?:ĐK\s+(\d+)|Cửa sổ\s+(\d+x\d+))', name, re.I)
    if not all((model, ratio, burden, turns, opening)):
        return None
    row['category'] = 'CT'
    row['sku'] = f'{model[1].upper()} {ratio[1]}/{ratio[2]}A CL{model[2]} {burden[1]}VA W{turns[1]}'
    row['specifications'] = {'Họ thiết bị': model[1].upper(), 'In (A)': ratio[1],
        'Dòng thứ cấp (A)': ratio[2], 'Cấp chính xác':model[2].replace(',', '.'),
        'Công suất':burden[1]+' VA', 'Số vòng dây':turns[1],
        'Cửa sổ':(opening[1] or opening[2])+' mm'}
    row['manufacturer_document'] = 'https://mitex.vn/'
    return row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html', type=Path)
    args = parser.parse_args()
    checked = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(args.html.read_text(encoding='utf8'), 'html.parser')
    rows = [row for card in soup.select('.product-container') if (row := parse_ct(card, checked))]
    if not rows:
        raise ValueError('No explicit priced CT configurations found; existing rows preserved')
    path = ROOT/'app/data/web_catalog_offers.json'
    payload = json.loads(path.read_text(encoding='utf8'))
    merged = {row['source_url']:row for row in payload['items']}
    merged.update({row['source_url']:row for row in rows})
    payload['items'] = list(merged.values())
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(f'Accepted {len(rows)} configurations; BD01: {sum(r["specifications"]["Họ thiết bị"]=="BD01" for r in rows)}')

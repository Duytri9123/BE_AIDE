import fitz
import re
import json

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')

def clean_price(val):
    if not val:
        return None
    # val might be '841500\n.' or '1.072.500\n. .' or '206800'
    text = str(val).split('\n')[0].strip().replace('.', '').replace(',', '').replace(' ', '')
    m = re.search(r'\d+', text)
    if m:
        num = int(m.group(0))
        if 1000 <= num <= 500000000:
            return num
    return None

sku_regex = re.compile(r'^[A-Z0-9]{2,}[A-Z0-9\-_/]{2,}$')

def is_sku(s):
    s = s.strip()
    if len(s) < 5 or len(s) > 20:
        return False
    if s.isdigit():
        return False
    # Exclude common Vietnamese words or headers
    if any(w in s.upper() for w in ['TIÊU', 'CHUẨN', 'BẢNG', 'GIÁ', 'DÒNG', 'CỰC', 'XUẤT', 'XỨ', 'TYPE', 'POLE']):
        return False
    return bool(sku_regex.match(s))

extracted = {}

for pno in range(len(doc)):
    page = doc[pno]
    tab_finder = page.find_tables()
    for tab in tab_finder.tables:
        df = tab.extract()
        for row in df:
            row = [c for c in row if c is not None]
            # row might have (sku, price) or (rating, sku, price) or (sku1, price1, sku2, price2)
            # handle multiline cells
            row_lines = [str(c).split('\n') for c in row]
            max_lines = max((len(l) for l in row_lines), default=0)
            
            for line_idx in range(max_lines):
                sub_row = []
                for l in row_lines:
                    sub_row.append(l[line_idx].strip() if line_idx < len(l) else '')
                
                # Scan sub_row for (sku, price) pairs
                for i in range(len(sub_row)):
                    c1 = sub_row[i]
                    if is_sku(c1):
                        # check next cells for price
                        for j in range(i + 1, min(len(sub_row), i + 3)):
                            p = clean_price(sub_row[j])
                            if p:
                                extracted[c1] = p
                                break

print(f"Extracted {len(extracted)} SKUs with prices from Schneider 2026 PDF!")
# Check against existing Schneider items in supplier_pricebooks.json
with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    sp_data = json.load(f)

sp_items = sp_data.get('items', [])
schneider_sp = [it for it in sp_items if it.get('brand') == 'Schneider Electric']
sp_skus = {it.get('sku'): it for it in schneider_sp if it.get('sku')}

matched = set(extracted.keys()) & set(sp_skus.keys())
print(f"Existing Schneider items in supplier_pricebooks.json: {len(schneider_sp)}")
print(f"Direct SKU matches: {len(matched)}")

# Sample matches
print("\nSample matched prices (Old price -> New 2026 price):")
for sku in list(matched)[:15]:
    old_p = sp_skus[sku].get('price')
    new_p = extracted[sku]
    print(f"  {sku}: {old_p} -> {new_p}")

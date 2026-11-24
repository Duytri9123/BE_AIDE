import fitz
import re
import json

doc = fitz.open(r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf')

sku_pattern = re.compile(r'^[A-Z0-9]{3,}[A-Z0-9\-_/]{1,15}$')
price_pattern = re.compile(r'^\d{1,3}(?:\.\d{3})+$|^\d{4,9}$')

def clean_price(val):
    s = val.strip().replace('.', '').replace(',', '').replace(' ', '')
    if s.isdigit():
        n = int(s)
        if 500 <= n <= 1000000000:
            return n
    return None

results = {} # sku -> (price, page_no)

for pno in range(len(doc)):
    page = doc[pno]
    words = page.get_text("words")
    # words: (x0, y0, x1, y1, word, block_no, line_no, word_no)
    # Group words by approx y (within 3 points)
    lines = {}
    for w in words:
        y_key = round(w[1] / 3.0) * 3.0
        lines.setdefault(y_key, []).append(w)
    
    for y_key, line_words in lines.items():
        # sort by x0
        line_words.sort(key=lambda x: x[0])
        for i in range(len(line_words)):
            w_text = line_words[i][4].strip()
            # check if w_text looks like SKU
            if sku_pattern.match(w_text) and not w_text.isdigit() and len(w_text) >= 5:
                # check next word on same line
                if i + 1 < len(line_words):
                    p_text = line_words[i+1][4].strip()
                    p = clean_price(p_text)
                    if p:
                        results[w_text] = (p, pno + 1)
                        continue
                # or check word 2 steps away (e.g. if there is a space or symbol)
                if i + 2 < len(line_words):
                    p_text = line_words[i+2][4].strip()
                    p = clean_price(p_text)
                    if p:
                        results[w_text] = (p, pno + 1)

print(f"Total extracted SKUs: {len(results)}")

# Check against supplier_pricebooks.json
with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    sp_data = json.load(f)

items = sp_data.get('items', [])
schneider_items = [it for it in items if it.get('brand') == 'Schneider Electric']
sp_skus = {it.get('sku'): it for it in schneider_items if it.get('sku')}

matched = set(results.keys()) & set(sp_skus.keys())
print(f"Schneider Electric items in DB: {len(schneider_items)}")
print(f"Matches in 2026 catalog: {len(matched)}")

# Show samples of updated prices
print("\nSample price updates:")
diff_count = 0
for sku in list(matched)[:20]:
    old_p = sp_skus[sku].get('price')
    new_p, pg = results[sku]
    if old_p != new_p:
        diff_count += 1
        print(f"  {sku} (page {pg}): {old_p} -> {new_p}")
print(f"Total changed prices among sample: {diff_count}")

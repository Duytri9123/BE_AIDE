"""Full updater for SINO and Schneider Electric catalogs."""
import os
import sys
import shutil
import json
import re
import fitz
import sqlite3
from datetime import datetime

sys.path.insert(0, 'BE_AIDE')
from scripts.build_sino_catalog import create_sino_items
from scripts.test_schneider_cad_linking import resolve_schneider_cad

PRICEBOOK_PATH = 'BE_AIDE/app/data/supplier_pricebooks.json'
BACKUP_PATH = 'BE_AIDE/app/data/supplier_pricebooks.json.bak_20261125'
SCHNEIDER_PDF = r'c:\Users\admin\Downloads\[SMALL SIZE] BANG GIA DAI LY 2026 (12).pdf'
DB_PATH = 'BE_AIDE/webbaogia.db'

def extract_schneider_pdf():
    print(f"Extracting prices from {SCHNEIDER_PDF}...")
    doc = fitz.open(SCHNEIDER_PDF)
    sku_pattern = re.compile(r'^[A-Z0-9]{3,}[A-Z0-9\-_/]{1,15}$')
    
    def clean_price(val):
        s = val.strip().replace('.', '').replace(',', '').replace(' ', '')
        if s.isdigit():
            n = int(s)
            if 500 <= n <= 1000000000:
                return n
        return None

    results = {}
    for pno in range(len(doc)):
        page = doc[pno]
        words = page.get_text("words")
        lines = {}
        for w in words:
            y_key = round(w[1] / 3.0) * 3.0
            lines.setdefault(y_key, []).append(w)
        
        for y_key, line_words in lines.items():
            line_words.sort(key=lambda x: x[0])
            for i in range(len(line_words)):
                w_text = line_words[i][4].strip()
                if sku_pattern.match(w_text) and not w_text.isdigit() and len(w_text) >= 5:
                    if i + 1 < len(line_words):
                        p = clean_price(line_words[i+1][4])
                        if p:
                            results[w_text] = (p, pno + 1)
                            continue
                    if i + 2 < len(line_words):
                        p = clean_price(line_words[i+2][4])
                        if p:
                            results[w_text] = (p, pno + 1)
    print(f"Extracted {len(results)} SKUs with prices from Schneider PDF.")
    return results

def main():
    # 1. Backup pricebook
    print(f"Backing up {PRICEBOOK_PATH} to {BACKUP_PATH}...")
    shutil.copy2(PRICEBOOK_PATH, BACKUP_PATH)

    # 2. Extract Schneider 2026 PDF prices
    sch_prices = extract_schneider_pdf()

    # 3. Load existing data
    with open(PRICEBOOK_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('items', [])
    manufacturers = data.get('manufacturers', {})
    print(f"Existing items in pricebook: {len(items)}")

    # 4. Remove any existing Sino items if present (clean slate)
    initial_count = len(items)
    items = [it for it in items if 'sino' not in (it.get('brand') or '').lower()]
    print(f"Removed {initial_count - len(items)} old Sino items.")

    # 5. Add new 184 Sino items
    sino_items = create_sino_items()
    print(f"Adding {len(sino_items)} new SINO items...")
    items.extend(sino_items)

    # Update manufacturers for Sino
    sino_models = {}
    for it in sino_items:
        m = it.get('sku') or it.get('name')
        sino_models.setdefault(m, []).append(it['id'])
    manufacturers['Sino - Vanlock'] = {'models': sino_models}
    manufacturers['Sino'] = {'models': sino_models}

    # 6. Update Schneider Electric items with 2026 prices and CAD links
    schneider_count = 0
    updated_price_count = 0
    linked_cad_count = 0

    for it in items:
        if (it.get('brand') or '').lower() == 'schneider electric':
            schneider_count += 1
            sku = it.get('sku')
            
            # Update price if found in 2026 catalog
            if sku and sku in sch_prices:
                new_price, page_no = sch_prices[sku]
                old_price = it.get('price')
                if old_price != new_price:
                    it['price'] = new_price
                    updated_price_count += 1
                    # Also update cells if price was recorded in cells
                    if it.get('cells') and it.get('columns'):
                        for idx, col in enumerate(it['columns']):
                            if any(term in col.lower() for term in ('giá', 'price', 'đơn giá')):
                                if idx < len(it['cells']):
                                    # Format formatted string matching original style
                                    it['cells'][idx] = f"{new_price:,}".replace(',', '.')
                it['edition'] = '2026'
                it['effective_date'] = '2026-01-01'
                it['source_page'] = page_no
                it['source_label'] = 'BẢNG GIÁ ĐẠI LÝ 2026 - SCHNEIDER ELECTRIC'
                it['price_note'] = 'Giá niêm yết theo Bảng giá Đại lý 2026 đã gồm VAT.'

            # Link CAD block if matching
            cad_id = resolve_schneider_cad(it)
            if cad_id:
                it['equipment_catalog_id'] = cad_id
                it['has_cad'] = True
                linked_cad_count += 1

    print(f"Schneider Electric items processed: {schneider_count}")
    print(f"Schneider prices updated to 2026: {updated_price_count}")
    print(f"Schneider items linked to CAD blocks: {linked_cad_count}")

    # 7. Save updated pricebook
    data['items'] = items
    data['manufacturers'] = manufacturers
    print(f"Saving updated pricebook with {len(items)} items to {PRICEBOOK_PATH}...")
    with open(PRICEBOOK_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Also sync to AIDE if public copy exists
    fe_pricebook = 'AIDE/packages/cad-viewer-example/public/catalog-data/supplier_pricebooks.json'
    if os.path.exists(fe_pricebook):
        print(f"Syncing to frontend copy {fe_pricebook}...")
        with open(fe_pricebook, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # 8. Update webbaogia.db brands
    if os.path.exists(DB_PATH):
        print(f"Updating brands in {DB_PATH}...")
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT name FROM brands WHERE name IN ('Sino', 'Sino - Vanlock')")
        existing_brands = [r[0] for r in cur.fetchall()]
        now_str = datetime.utcnow().isoformat()
        if 'Sino' not in existing_brands:
            cur.execute("INSERT INTO brands (name, created_at, updated_at) VALUES (?, ?, ?)", ('Sino', now_str, now_str))
            print("  Inserted brand 'Sino'")
        if 'Sino - Vanlock' not in existing_brands:
            cur.execute("INSERT INTO brands (name, created_at, updated_at) VALUES (?, ?, ?)", ('Sino - Vanlock', now_str, now_str))
            print("  Inserted brand 'Sino - Vanlock'")
        conn.commit()
        conn.close()

    print("\nSUCCESS: All catalogs updated cleanly!")

if __name__ == '__main__':
    main()

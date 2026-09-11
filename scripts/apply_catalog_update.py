"""
Apply Catalog Update from User Input
Updates BE_BOM catalog_data.json, FE_Electric catalog_data.json,
and triggers multi-format export and DB seed.
"""
import json
import os
import re
import sys

def main():
    transcript_path = r'C:\Users\QUANG HUAN\.gemini\antigravity-ide\brain\4372818d-c05d-4f19-93dc-1d46302014a2\.system_generated\logs\transcript_full.jsonl'
    if not os.path.exists(transcript_path):
        print(f"[ERROR] Transcript not found: {transcript_path}")
        sys.exit(1)

    user_prompt = ""
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if data.get('type') == 'USER_INPUT':
                user_prompt = data.get('content', '')
                break

    if not user_prompt:
        print("[ERROR] No user input found in transcript.")
        sys.exit(1)

    # Cut off truncation notice if present
    idx_trunc = user_prompt.find('<truncated')
    clean_prompt = user_prompt[:idx_trunc] if idx_trunc != -1 else user_prompt
    matches = [m.start() for m in re.finditer(r'(\r?\n    \},)', clean_prompt)]
    if not matches:
        print("[ERROR] Could not find valid item delimiters in user input.")
        sys.exit(1)

    valid_json = clean_prompt[clean_prompt.find('['):matches[-1]] + '\n    }\n]'
    user_items = json.loads(valid_json)
    print(f"[INFO] Successfully parsed {len(user_items)} complete items from user message.")

    be_cat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "catalog_data.json"))
    fe_cat_path = r'C:\WebBaoGia\FE_Electric\src\data\catalog_data.json'

    with open(be_cat_path, 'r', encoding='utf-8') as f:
        cat_items = json.load(f)

    cat_by_sku = {it.get('ma'): it for it in cat_items if it.get('ma')}
    premium_series = {'LA63L', 'ABS203c', 'ABS403c', 'ABS404c', 'LA63H', 'LA125H'}

    updated_skus = []
    for u_item in user_items:
        sku = u_item.get('ma')
        if not sku:
            continue
        if sku in cat_by_sku:
            existing = cat_by_sku[sku]
            for k, v in u_item.items():
                if k in ['brand', 'brand_display']:
                    continue
                existing[k] = v

            # Standardize brand / brand_display
            series = existing.get('series')
            if series in premium_series:
                existing['brand'] = 'ls_premium'
                existing['brand_display'] = 'LS (premium)'
            else:
                existing['brand'] = 'ls_standard'
                existing['brand_display'] = 'LS (standard)'

            updated_skus.append(sku)
        else:
            # New item
            new_item = dict(u_item)
            series = new_item.get('series')
            if series in premium_series:
                new_item['brand'] = 'ls_premium'
                new_item['brand_display'] = 'LS (premium)'
            else:
                new_item['brand'] = 'ls_standard'
                new_item['brand_display'] = 'LS (standard)'
            cat_items.append(new_item)
            cat_by_sku[sku] = new_item
            updated_skus.append(sku)

    print(f"[INFO] Applied updates to {len(updated_skus)} devices.")

    # 1. Save BE_BOM catalog_data.json
    with open(be_cat_path, 'w', encoding='utf-8') as f:
        json.dump(cat_items, f, ensure_ascii=False, indent=4)
    print(f"[SUCCESS] Saved {be_cat_path} (Total items: {len(cat_items)})")

    # 2. Save FE_Electric catalog_data.json if exists
    if os.path.exists(fe_cat_path):
        with open(fe_cat_path, 'w', encoding='utf-8') as f:
            json.dump(cat_items, f, ensure_ascii=False, indent=4)
        print(f"[SUCCESS] Synchronized {fe_cat_path}")

    # 3. Export all formats
    try:
        from scripts.export_catalog import export_all
    except ImportError:
        import importlib
        export_all = importlib.import_module("export_catalog").export_all
    export_all()

    # 4. Seed database
    import asyncio
    try:
        from scripts.seed_devices_catalog import seed_catalog
    except ImportError:
        import importlib
        seed_catalog = importlib.import_module("seed_devices_catalog").seed_catalog
    asyncio.run(seed_catalog())

    print("[SUCCESS] All catalog updates, exports, and database seeds finished successfully!")

if __name__ == "__main__":
    main()

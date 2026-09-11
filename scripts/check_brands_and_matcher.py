import asyncio
import sys
from app.services.device_catalog_engine import DeviceCatalogEngine

sys.stdout.reconfigure(encoding='utf-8')

eng = DeviceCatalogEngine()

test_devices = [
    {"name": "MCCB 2P 40A", "spec": "2P 40A 10kA", "category": "MCCB", "poles": 2, "in_a": 40, "icu_ka": 10},
    {"name": "Contactor 2P 40A", "spec": "2P 40A", "category": "Contactor", "poles": 2, "in_a": 40, "icu_ka": None},
    {"name": "MCB 2P 16A", "spec": "2P 16A 6kA", "category": "MCB", "poles": 2, "in_a": 16, "icu_ka": 6},
    {"name": "MCB 2P 32A", "spec": "2P 32A 6kA", "category": "MCB", "poles": 2, "in_a": 32, "icu_ka": 6},
]

brands = ["ls_standard", "schneider", "mitsubishi", "abb", "chint"]

print("--- TESTING MULTI-BRAND MATCHING ---")
for d in test_devices:
    print(f"\nDevice: {d['name']} ({d['spec']}):")
    for b in brands:
        matches = eng.filter_devices(
            brand=b,
            device_type=d['category'],
            poles=d['poles'],
            in_current=d['in_a'],
            limit=3
        )
        if matches:
            m = matches[0]
            print(f"  [{b.upper()}] => SKU: {m.get('sku')} | Name: {m.get('name')} | Price: {m.get('price'):,} đ")
        else:
            # Try fuzzy match
            text_query = f"{b} {d['category']} {d['poles']}P {int(d['in_a'])}A"
            f_matches = eng.match_from_text(text_query)
            if f_matches:
                fm, score = f_matches[0]
                print(f"  [{b.upper()} (Fuzzy)] => SKU: {fm.get('sku')} | Name: {fm.get('name')} | Price: {fm.get('price', 0):,} đ")
            else:
                print(f"  [{b.upper()}] => (Không có model chính xác trong DB, dùng ước tính)")

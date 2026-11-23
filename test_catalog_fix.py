"""
Test functional: verify suggest_takeoff_products parse in_a/poles từ name khi spec rỗng
"""
import sys
sys.path.insert(0, 'E:/duytristool/AIDE_website/BE_AIDE')

from app.services.ai.takeoff_catalog import suggest_takeoff_products

# Giả lập devices với thông số nằm trong name (spec rỗng) - case hay bị lỗi
test_devices = [
    # Case 1: thông số chỉ có trong name
    {'category': 'MCB', 'name': 'MCB 3P-32A 6kA', 'spec': '', 'quantity': 1, 'unit': 'Cái'},
    # Case 2: thông số trong cả name và spec
    {'category': 'MCCB', 'name': 'MCCB 3 pha 100A', 'spec': '25kA, 380V', 'quantity': 1, 'unit': 'Cái'},
    # Case 3: Aptomat (generic) với thông số trong name
    {'category': 'APTOMAT', 'name': 'Aptomat 2P 16A', 'spec': '', 'quantity': 2, 'unit': 'Cái'},
    # Case 4: rated_current field thay cho in_a
    {'category': 'MCB', 'name': 'MCB 1P', 'spec': '', 'rated_current': 10, 'quantity': 1, 'unit': 'Cái'},
    # Case 5: Contactor với in_a trong spec
    {'category': 'CONTACTOR', 'name': 'Contactor', 'spec': '32A 220V', 'quantity': 1, 'unit': 'Cái'},
    # Case 6: Đèn báo - auxiliary category
    {'category': 'PILOT_LIGHT', 'name': 'Đèn báo pha R', 'spec': '220V', 'quantity': 3, 'unit': 'Cái'},
]

results = suggest_takeoff_products(test_devices)
print(f"\n{'='*60}")
print(f"Results for {len(test_devices)} devices:")
print(f"{'='*60}")
for d in test_devices:
    name = d['name']
    status = d.get('selection_analysis', {}).get('status', 'NO_ANALYSIS')
    candidates = d.get('catalog_candidates', {})
    num_brands = len(candidates)
    num_items = sum(len(v) for v in candidates.values())
    print(f"\n[{name}]")
    print(f"  Status: {status}")
    print(f"  Brands found: {num_brands}, Items: {num_items}")
    if candidates:
        for brand, items in list(candidates.items())[:2]:
            print(f"    {brand}: {items[0].get('sku','?')} - {items[0].get('name','?')[:50]}")
    elif status == 'insufficient_source_specs':
        print(f"  Reason: {d.get('selection_analysis',{}).get('reason','')}")

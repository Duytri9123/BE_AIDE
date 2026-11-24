import json

with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('items', [])
print(f"Total items in supplier_pricebooks.json: {len(items)}")

brands = {}
for it in items:
    b = it.get('brand')
    brands[b] = brands.get(b, 0) + 1

for b, cnt in sorted(brands.items(), key=lambda x: -x[1]):
    print(f"  {b}: {cnt} items")

print("\nSample item from Shihlin:")
shihlin_items = [it for it in items if it.get('brand') == 'Shihlin']
if shihlin_items:
    print(json.dumps(shihlin_items[0], ensure_ascii=False, indent=2))

print("\nSample item from Schneider:")
schneider_items = [it for it in items if (it.get('brand') or '').lower() == 'schneider']
if schneider_items:
    print(json.dumps(schneider_items[0], ensure_ascii=False, indent=2))

print("\nSample item from Sino (if any):")
sino_items = [it for it in items if 'sino' in (it.get('brand') or '').lower()]
print(f"Sino items count: {len(sino_items)}")

import json

with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('items', [])
schneider_items = [it for it in items if it.get('brand') == 'Schneider Electric']
print(f"Schneider Electric items: {len(schneider_items)}")
if schneider_items:
    print("Sample Schneider item:")
    print(json.dumps(schneider_items[0], ensure_ascii=False, indent=2))
    print("\nSample Schneider groups:")
    groups = {}
    for it in schneider_items:
        g = it.get('group', 'No group')
        groups[g] = groups.get(g, 0) + 1
    for g, cnt in list(groups.items())[:15]:
        print(f"  {g}: {cnt} items")

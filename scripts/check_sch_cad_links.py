import json

with open('BE_AIDE/app/data/supplier_pricebooks.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('items', [])
schneider_items = [it for it in items if it.get('brand') == 'Schneider Electric']
with_cad = [it for it in schneider_items if it.get('equipment_catalog_id')]

print(f"Schneider Electric items: {len(schneider_items)}")
print(f"Schneider items with equipment_catalog_id: {len(with_cad)}")

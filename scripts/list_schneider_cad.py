import json

with open(r'E:\duytristool\AIDE_website\BE_AIDE\data\CatalogTB\_agent_index\browser_display_v6.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data.get('items', [])
schneider_cad_items = [it for it in items if it.get('brand') == 'Schneider Electric']
for it in schneider_cad_items[30:70]:
    print(f"id={it.get('id')} | code={it.get('product_code')} | name={it.get('name')}")

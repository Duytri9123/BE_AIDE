import sys
sys.path.insert(0, 'BE_AIDE')
from app.services.device_catalog_browser import build_catalog_page, customer_catalog_page, load_supplier_items
from app.services.ai.device_price_resolver import CustomPriceStore

supplier_items = load_supplier_items()
print(f"Loaded {len(supplier_items)} supplier items.")

# Test Sino
sino_res = customer_catalog_page(build_catalog_page([], CustomPriceStore.list_all(), supplier_items=supplier_items, brand='Sino', limit=5))
print(f"Sino query result: total = {sino_res.get('total')}")
for it in sino_res.get('items', [])[:3]:
    print(f"  Item: {it.get('item_name')} | group: {it.get('group')} | image_url: {it.get('image_url')} | cols: {it.get('columns')} | cells: {it.get('cells')}")

# Test Schneider
sch_res = customer_catalog_page(build_catalog_page([], CustomPriceStore.list_all(), supplier_items=supplier_items, brand='Schneider Electric', limit=5))
print(f"\nSchneider query result: total = {sch_res.get('total')}")
sch_all_cad = [it for it in supplier_items if it.get('brand') == 'Schneider Electric' and it.get('has_cad')]
print(f"Total Schneider items with CAD in full supplier list: {len(sch_all_cad)}")
for it in sch_all_cad[:3]:
    print(f"  CAD item: {it.get('item_name')} | cad_id: {it.get('equipment_catalog_id')} | sku: {it.get('sku')} | price: {it.get('price')}")

import sys
sys.path.insert(0, 'BE_AIDE')
from app.services.catalogtb_browser import browser_data

b = browser_data()
items = b.get('items', [])
sch_items = [it for it in items if 'schneider' in str(it).lower() or 'ik60' in str(it).lower() or 'cvs' in str(it).lower()]
print(f"Total matching: {len(sch_items)}")
for it in sch_items[:10]:
    print(f"id={it.get('id')} | brand={it.get('brand')} | name={it.get('name')} | code={it.get('product_code')} | cat={it.get('category')} | display={it.get('display')}")

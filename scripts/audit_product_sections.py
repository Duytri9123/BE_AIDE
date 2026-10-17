"""Audit current/same-brand/other-brand pole constraints for every device."""
import json
import sys
from collections import Counter,defaultdict
from pathlib import Path
from app.services.catalogtb_browser import _build_browser_data
from app.services.catalog_family_matching import category_key
from app.services.catalog_product_sections import candidate_rows,pole_compatible
from app.services.library_catalog_information import source_rows

def main():
    snapshot=Path(__file__).resolve().parents[1]/'tmp/catalog-research/audit-inventory.json'
    data=json.loads(snapshot.read_text(encoding='utf8')) if '--saved-inventory' in sys.argv else _build_browser_data()
    pools=defaultdict(list)
    for row in source_rows():pools[category_key(row.get('category'))].append(row)
    errors=[];brands=defaultdict(Counter);same_total=0;other_total=0
    for device in data['items']:
        brand=device.get('brand') or 'Chưa xác định';brands[brand]['devices']+=1
        pool=pools[category_key(device.get('type'))]
        for other in (False,True):
            rows=candidate_rows(device,pool,other)
            name='other_brand_candidates' if other else 'same_brand_candidates'
            brands[brand][name]+=len(rows)
            if rows:brands[brand]['devices_with_'+name]+=1
            for row in rows:
                if not pole_compatible(device,row):errors.append({'device':device['id'],'issue':'wrong_poles'})
            if other:other_total+=len(rows)
            else:same_total+=len(rows)
    report={'devices_checked':len(data['items']),'manufacturers_checked':len(brands),
            'same_brand_candidates':same_total,'other_brand_candidates':other_total,
            'brands':{k:dict(v) for k,v in sorted(brands.items())},'errors':errors,
            'scope':'All catalog devices; compatible known type/poles and rating checks. Replacement candidates require final electrical and mechanical confirmation.'}
    target=Path(__file__).resolve().parents[1]/'docs/all-product-sections-audit.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='brands'}),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()

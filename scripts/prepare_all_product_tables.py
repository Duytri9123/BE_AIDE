"""Prepare all three real product sections per saved device for exhaustive UI QA.

Fixtures stay private; this never substitutes invented catalog data.
"""
import json
from collections import defaultdict, Counter
from pathlib import Path
from app.services.customer_equipment_information import customer_information_rows,customer_device
from app.services.library_catalog_information import information_rows,source_rows
from app.services.catalog_product_sections import candidate_rows
from app.services.catalog_family_matching import category_key
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.catalog_verified_configuration import apply_verified_configuration

ROOT=Path(__file__).resolve().parents[1]

def main():
    inventory=json.loads((ROOT/'tmp/catalog-research/audit-inventory.json').read_text(encoding='utf8'))
    target=ROOT/'tmp/all-product-tables';target.mkdir(exist_ok=True)
    by_brand=defaultdict(list);by_type=defaultdict(list)
    for row in source_rows():
        by_brand[canonical_brand(row.get('brand'))].append(row)
        by_type[category_key(row.get('category'))].append(row)
    counts=Counter();devices=[]
    for n,device in enumerate(inventory['items'],1):
        apply_verified_configuration(device)
        pool=by_brand[canonical_brand(device.get('brand'))] if device.get('brand') else source_rows()
        current=information_rows(device,pool)
        if device.get('product_code'):
            current=[r for r in current if r.get('match_scope')=='source_family' or r.get('sku')==device['product_code']]
        sections={'current':customer_information_rows(current,device)}
        existing={r.get('sku') for r in current if r.get('match_scope')=='source_family'}
        for scope,other in [('same_brand',False),('other_brands',True)]:
            rows=[]
            for row in candidate_rows(device,by_type[category_key(device.get('type'))],other):
                if not other and row.get('sku') in existing:continue
                public=customer_information_rows([row],{**device,'brand':row['brand']})
                rows.extend(r for r in public if r.get('id')!=device['id'])
            sections[scope]=rows
        for scope,rows in sections.items():counts[scope+'_rows']+=len(rows)
        (target/(device['id']+'.json')).write_text(json.dumps(sections,ensure_ascii=False),encoding='utf8')
        devices.append(customer_device(device))
        if n%100==0:print(f'Prepared {n}/{len(inventory["items"])} devices',flush=True)
    (target/'devices.json').write_text(json.dumps(devices,ensure_ascii=False),encoding='utf8')
    report={'devices':len(devices),**counts,'inventory':'Saved authoritative inventory; real current source rows and production selectors/serializers.'}
    (ROOT/'docs/all-product-tables-data-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)

if __name__=='__main__':main()

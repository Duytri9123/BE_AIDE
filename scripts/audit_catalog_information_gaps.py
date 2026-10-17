"""Find real catalog coverage gaps, excluding generated CAD information rows."""
import json
import sys
from pathlib import Path
from collections import Counter
from app.services.catalogtb_browser import _build_browser_data
from app.services.library_catalog_information import information_rows,source_rows
from app.services.customer_equipment_information import external_url,product_specs

ROOT=Path(__file__).resolve().parents[1]

def main():
    print('Building authoritative catalog inventory',flush=True)
    cached=ROOT/'tmp/catalog-research/audit-inventory.json'
    data=json.loads(cached.read_text(encoding='utf8')) if '--saved-inventory' in sys.argv else _build_browser_data()
    pool=source_rows();gaps=[];covered=0;counts=Counter()
    (ROOT/'tmp/catalog-research').mkdir(parents=True,exist_ok=True)
    (ROOT/'tmp/catalog-research/audit-inventory.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
    print(f'Inventory ready: {data["total"]} devices, {len(pool)} catalog rows',flush=True)
    for index,device in enumerate(data['items'],1):
        if index%50==0:print(f'Checking {index}/{data["total"]}',flush=True)
        rows=information_rows(device,pool)
        actual=[r for r in rows if r.get('information_kind') in {'pricebook','manufacturer_catalog','price_reference'} and external_url(r.get('source_url')) and (not device.get('product_code') or r.get('match_scope')=='source_family' or r.get('sku')==device.get('product_code'))]
        if actual:covered+=1;continue
        urls=[device.get('manufacturer_document'),*(o.get('source_url') for o in (device.get('catalog_references') or {}).get('options',[]))]
        gaps.append({'id':device['id'],'name':device['display'],'brand':device.get('brand'),
            'model':device.get('product_code'),'type':device.get('type'),'specifications':product_specs(device.get('spec')),
            'external_documents':list(dict.fromkeys(u for value in urls if (u:=external_url(value))))})
        counts[device.get('brand') or 'Chưa xác định']+=1
        if index%200==0:print(f'Checked {index}/{data["total"]}',flush=True)
    report={'devices_checked':data['total'],'with_external_catalog_rows':covered,'without_external_catalog_rows':len(gaps),
            'without_identified_model':sum(not g['model'] for g in gaps),
            'gaps_by_device_type':dict(Counter(g['type'] or 'Chưa xác định' for g in gaps)),
            'gaps_by_manufacturer':dict(counts),'scope':'Generated CAD facts and generic reference options are not counted as external catalog coverage.'}
    (ROOT/'tmp/catalog-research').mkdir(parents=True,exist_ok=True)
    (ROOT/'tmp/catalog-research/information-gaps.json').write_text(json.dumps(gaps,ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'docs/catalog-information-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=True),flush=True)

if __name__=='__main__':main()

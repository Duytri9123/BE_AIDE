"""Validate manufacturer separation across a freshly built complete catalog."""
import json
from pathlib import Path
from app.services.catalogtb_browser import _build_browser_data
from app.services.customer_equipment_information import customer_device
from app.services.ai.manufacturer_registry import canonical_brand

def main():
    rows=_build_browser_data()['items'];errors=[];with_other=0;other_count=0
    for raw in rows:
        device=customer_device(raw);maker=canonical_brand(device.get('brand'))
        own=device['catalog_references']['options'];other=device['other_brand_references']
        if other:with_other+=1;other_count+=len(other)
        for options,is_other in ((own,False),(other,True)):
            ids=[(o['brand'],o['model'].casefold()) for o in options]
            if len(ids)!=len(set(ids)):errors.append({'id':device['id'],'error':'duplicate'})
            if maker and any((canonical_brand(o['brand'])!=maker)!=is_other for o in options):
                errors.append({'id':device['id'],'error':'wrong_section'})
    report={'devices_checked':len(rows),'devices_with_other_manufacturers':with_other,
            'other_manufacturer_references':other_count,'errors':errors,'scope':'Fresh complete catalog, customer serialization and deduplication; substitution compatibility is not verified.'}
    target=Path(__file__).resolve().parents[1]/'docs/all-device-reference-sections-check.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report),flush=True)
    if errors:raise SystemExit(1)

if __name__=='__main__':main()

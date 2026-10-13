"""Audit prices and expose exact Mitsubishi frame/pole configurations for browsing.

Run: python -m scripts.audit_library_price_coverage. No geometry approval is inferred.
"""
import json
import re
from collections import Counter
from pathlib import Path
from app.services.catalogtb_browser import browser_data
from app.services.device_catalog_browser import build_catalog_page, load_supplier_items, load_web_offers, load_catalog_documents
from app.services.ai.device_price_resolver import CustomPriceStore
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.pricebook_library_links import PRICE_OPTIONS_PATH, load_links


def build_options(devices, rows):
    options, pending = [], []
    for row in rows:
        if canonical_brand(row.get('brand')) != 'Mitsubishi Electric' or row.get('category') != 'MCCB':
            continue
        match = re.fullmatch(r'(NF[\w-]+)\s+([234]P)\s+(\d+(?:\.\d+)?)A', row.get('item_name', ''), re.I)
        if not match or not row.get('source_sha256') or row.get('source_kind') != 'supplier_pricebook':
            continue
        model, poles, current = match.groups()
        if (row.get('specifications') or {}).get('Số cực', '').upper() != poles.upper():
            continue
        hits = [d for d in devices if canonical_brand(d.get('brand')) == 'Mitsubishi Electric'
                and d.get('brand_identification_status') == 'verified'
                and d.get('type', '').upper() == 'MCCB'
                and str(d.get('product_code') or '').upper() == model.upper()
                and str((d.get('spec') or {}).get('so_cuc') or '').upper() == poles.upper()]
        if len(hits) != 1:
            pending.append({'price_row_id':row['id'], 'model':model, 'poles':poles,
                            'reason':'missing_or_ambiguous_CAD'})
            continue
        options.append({'price_row_id':row['id'], 'equipment_catalog_id':hits[0]['id'],
                        'status':'configuration_option', 'model':model, 'poles':poles,
                        'current_a':float(current), 'source_sha256':row['source_sha256'],
                        'identity_evidence':f"Workbook {row.get('source_sheet')} row {row.get('source_row')}: {model} {poles}; CAD metadata identifies the same maker, full model and poles. In is a price option, not a verified CAD rating.",
                        'cad_insertion_verified':False})
    return options, pending


def main():
    devices = browser_data()['items']
    page = build_catalog_page([], CustomPriceStore.list_all(), supplier_items=load_supplier_items(),
                              web_offers=load_web_offers(), documents=load_catalog_documents())
    options, pending = build_options(devices, load_supplier_items())
    PRICE_OPTIONS_PATH.write_text(json.dumps({'schema_version':1,
        'relationship':'equipment_one_to_price_configuration_options_many',
        'scope':'Mitsubishi MCCB full model and poles; browsing only',
        'options':options},ensure_ascii=False,indent=2),encoding='utf8')
    cad_counts = Counter(canonical_brand(d.get('brand')) for d in devices)
    brands = [{'name':m['name'], 'price_count':m['price_count'], 'cad_count':cad_counts[m['name']],
               'status':'available' if m['price_count'] else 'missing_price_data'} for m in page['brands']]
    report = {'brands':brands, 'priced_total':page['priced_total'], 'verified_cad_links':len(load_links()),
              'configuration_options':len(options),
              'devices_with_price_options':len({o['equipment_catalog_id'] for o in options}), 'pending':pending}
    out = Path('tmp/library-price-coverage.json');out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('brands','pending')}))


if __name__ == '__main__':
    main()

"""Reproducible audit of verified makers without published CAD price choices.

Text overlap is a diagnostic lead, never an approved SKU/geometry link.
"""
import json
import re
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import browser_data
from app.services.library_price_matching import configuration_links
from app.services.ai.takeoff_pricebook import published_rows
from app.services.ai.manufacturer_registry import canonical_brand


def norm(text):
    return re.sub(r'[^A-Z0-9]','',str(text or '').upper())


def audit(devices,prices):
    makers=defaultdict(list)
    for row in prices:makers[canonical_brand(row['brand'])].append(row)
    gaps=[];linked=[]
    for device in devices:
        links=configuration_links(device,prices)
        if links:linked.append({'id':device['id'],'brand':device.get('brand'),'name':device.get('display') or device.get('name'),'choices':len(links)})
        if links or device.get('brand_identification_status')!='verified':continue
        pool=makers[canonical_brand(device.get('brand'))]
        code=str(device.get('product_code') or '')
        codes=[x.strip() for x in re.split(r'\s+/\s+',code) if x.strip()]
        codes += (device.get('ai_identification') or {}).get('cac_ma_dong_san_pham') or []
        codes += (device.get('reviewed_description') or {}).get('price_family_codes') or []
        similar=[r for r in pool if any(norm(c) and norm(c) in norm(r.get('sku','')+' '+r.get('item_name','')) for c in codes)]
        reason='no_brand_prices' if not pool else 'no_device_code' if not codes else 'related_code_only' if similar else 'code_not_in_published_prices'
        gaps.append({'id':device['id'],'name':device.get('display') or device.get('name'),'brand':device.get('brand'),
                     'type':device.get('type'),'product_code':code,'reason':reason,
                     'brand_price_count':len(pool),'related_price_rows':[{k:r.get(k) for k in ('id','sku','item_name','category','specifications')} for r in similar[:5]]})
    return {'linked_count':len(linked),'verified_unlinked_count':len(gaps),'reason_counts':dict(Counter(d['reason'] for d in gaps)),
            'price_row_count':len(prices),'linked':linked,'gaps':gaps}


if __name__=='__main__':
    data=audit(browser_data()['items'],published_rows())
    (ROOT/'docs/library-verified-price-gaps.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in data.items() if k not in ('linked','gaps')},ensure_ascii=False))

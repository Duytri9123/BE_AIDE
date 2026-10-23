"""Live prices for explicitly documented catalog references, never CAD identity.

Reference choices may have another maker/model. They must remain visibly
separate from a price matched to the original drawing.
"""
import re
from collections import defaultdict
from threading import Lock

_price_index_lock = Lock()
_price_index_rows = None
_price_index_value = None
from app.services.ai.manufacturer_registry import canonical_brand


def category(value):
    value = re.sub(r'[\s_-]', '', str(value or '')).upper()
    return {'INDICATOR':'LIGHT', 'PILOTLAMP':'LIGHT', 'PILOTLIGHT':'LIGHT',
            'SELECTOR':'SELECTORSWITCH', 'FUSEASSEMBLY':'FUSEHOLDER',
            'INVERTER':'VFD', 'TERMINAL':'TERMINALBLOCK','ZCT':'CT',
            'CUỘNKHÁNGBAPHALÕITHÉP':'REACTOR',
            'INTERLOCK':'ACCESSORY','AUXCONTACT':'ACCESSORY'}.get(value,value)


def price_index(rows):
    if isinstance(rows,dict):return rows
    index=defaultdict(list)
    from .reviewed_product_taxonomy import reviewed_price_row
    for original in rows:
        row=reviewed_price_row(original)
        index[(canonical_brand(row.get('brand')),category(row.get('category')))].append(row)
    return index


def reference_matches(option, kind, rows):
    brand = canonical_brand(option.get('brand'))
    model = str(option.get('model') or '').strip().upper()
    source_id = option.get('source_row_id')
    if not brand or (not source_id and not re.search(r'[A-Z]',model)) or model.startswith('*') or model in {'---','MẶT TRƯỚC','MẶT BÊN'}:
        return []
    kinds={'NGUỒNVÀBIẾNÁP':('TRANSFORMER','POWERSUPPLY')}.get(category(kind),(category(kind),))
    index=price_index(rows)
    pool = [r for expected in kinds for r in index.get((brand,expected),[])]
    if source_id:
        # An explicit row identity is authoritative; a missing row is not
        # silently replaced by another voltage/current variant.
        return [r for r in pool if r['id']==source_id]
    codes = [re.sub(r'\s+\.(?=\d)', '.', s.strip()) for s in re.split(r'\s+/\s+',model)]
    result=[]
    for row in pool:
        sku = str(row.get('sku') or '').strip().upper()
        if any(sku==code or re.match(re.escape(code)+r'(?=$|[\s/.-])',sku) for code in codes):
            result.append(row)
    return result


def priced_references(device, rows):
    rows=price_index(rows)
    references = device.get('catalog_references') or {}
    kind = references.get('category') or device.get('type')
    result=[]
    from .catalog_other_manufacturers import other_manufacturer_options
    unique={}
    for original in [*references.get('options',[]),*other_manufacturer_options(device)]:
        unique.setdefault((canonical_brand(original.get('brand')),original.get('model')),original)
    for original in unique.values():
        option=dict(original)
        matches=reference_matches(option,kind,rows)
        option['price_choices']=[{'price_row_id':r['id'],'model':r['sku'],'price':r['price'],
                                  'vat_status':r.get('vat_status'),'checked_at':r.get('checked_at')}
                                 for r in matches]
        # A family has several prices; do not present a single arbitrary price.
        option['price']=matches[0]['price'] if len(matches)==1 else None
        result.append(option)
    return {**references,'options':result}


def reference_rows(device, rows):
    rows=price_index(rows)
    references=device.get('catalog_references') or {}
    kind=references.get('category') or device.get('type')
    selected={}
    for option in references.get('options',[]):
        for row in reference_matches(option,kind,rows):
            selected[row['id']]=row
    return list(selected.values())


def published_price_index():
    """Reuse the index while the revision-aware published row list is unchanged."""
    from app.services.ai.takeoff_pricebook import published_rows
    global _price_index_rows, _price_index_value
    rows = published_rows()
    with _price_index_lock:
        if rows is not _price_index_rows:
            _price_index_value = price_index(rows)
            _price_index_rows = rows
        return _price_index_value


def enrich_browser_prices(payload):
    rows=published_price_index()
    items=[]
    for device in payload['items']:
        references=priced_references(device,rows)
        # Preserve source identity; expose catalog codes under a separate name.
        codes=list(dict.fromkeys(c['model'] for o in references.get('options',[])
                                for c in o.get('price_choices',[])))
        codes=list(dict.fromkeys([*codes,*[o['model'] for o in references.get('options',[])
            if o.get('source_url') and re.search(r'[A-Za-z].*\d|\d.*[A-Za-z]|^\d{5,}$',str(o.get('model') or ''))
            and not str(o['model']).startswith('*')]]))
        items.append({**device,'catalog_references':references,'reference_product_codes':codes})
    return {**payload,'items':items}

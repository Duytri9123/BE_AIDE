"""Link takeoff devices to published price rows, independently of CAD approval."""
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.device_catalog_browser import build_catalog_page, load_supplier_items, load_web_offers
from app.services.ai.device_price_resolver import CustomPriceStore, CUSTOM_PRICES_PATH
from app.services.pricebook_library_links import load_links, load_price_options


def public_id(row):
    return hashlib.sha256(row['id'].encode()).hexdigest()[:24]


@lru_cache(maxsize=1)
def _published_rows(revision):
    return build_catalog_page([], CustomPriceStore.list_all(), supplier_items=load_supplier_items(),
                              web_offers=load_web_offers(), library_links=load_links(), limit=100000)['items']


def published_rows():
    root = Path(__file__).resolve().parents[2] / 'data'
    files = [root / name for name in ('supplier_pricebooks.json', 'web_catalog_offers.json',
                                     'pricebook_library_links.json')]+[Path(CUSTOM_PRICES_PATH)]
    revision = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files if p.is_file())
    return _published_rows(revision)


def _norm(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).upper()


def _values(row, field):
    spec = row.get('specifications') or {}
    keys = {'poles':('Số cực', 'Poles', 'so_cuc'), 'current':('In (A)', 'Dòng định mức (A)', 'Rated current (A)'),
            'icu':('Icu(KA)', 'Icu (kA)', 'Khả năng cắt và điện áp')}[field]
    text = ' '.join(str(spec.get(k) or '') for k in keys)
    if field == 'poles':
        text += ' ' + str(row.get('item_name') or '') + ' ' + str(row.get('group') or '')
        return [float(v) for v in re.findall(r'(?<!\w)(\d+)\s*(?:P|POLES?)\b', text, re.I)]
    if field == 'current':
        text = re.sub(r'\([^)]*\)', '', text)
    if field == 'current' and not text.strip():
        return [float(v.replace(',', '.')) for v in re.findall(r'(?<!\w)(\d+(?:[.,]\d+)?)\s*A\b',str(row.get('item_name') or ''),re.I)]
    if field == 'icu':
        return [float(v.replace(',', '.')) for v in re.findall(r'(\d+(?:[.,]\d+)?)\s*kA', text,re.I)] or ([float(text)] if re.fullmatch(r'\s*\d+(?:\.\d+)?\s*',text) else [])
    return [float(v.replace(',', '.')) for v in re.findall(r'\d+(?:[.,]\d+)?', text)]


def match_device(device, rows, *, candidate_limit=30):
    brand = str(device.get('brand') or device.get('detected_brand') or device.get('origin') or '').strip()
    known_brand = brand.casefold() not in {'', 'asian', 'asia', 'oem', '-', '---', 'chưa xác định'}
    code = _norm(device.get('part_number') or device.get('sku'))
    category = _norm(device.get('category'))
    kinds = {'MCB','MCCB','ACB','RCBO','RCCB'} if category == 'CB' else {category}
    selected = device.get('selected_product') or {}
    selected_id = selected.get('price_row_id') if device.get('selection_source')=='user_selected' else None
    matches = []
    for row in rows:
        if row.get('category') not in kinds or (known_brand and canonical_brand(row['brand']) != canonical_brand(brand)):
            continue
        label, sku = _norm(row.get('item_name')), _norm(row.get('sku'))
        exact = bool(code and code in {label, sku})
        model_match = bool(code and re.match(re.escape(code)+r'(?=\s|$)', label))
        # Reviewed ABB pricebooks distinguish the CAD frame (A1/A2/A3)
        # from ordering series (A1A/A1B/A1C/A1N). Frame matches are choices,
        # never an automatically approved order code.
        family_match = bool(known_brand and canonical_brand(brand) == 'ABB'
                            and category == 'MCCB' and code in {'A1', 'A2', 'A3'}
                            and (row.get('specifications') or {}).get('Họ thiết bị') == code
                            and re.match(re.escape(code)+r'[A-Z](?=\s|$)', label))
        body_match = bool(known_brand and canonical_brand(brand) == 'ABB'
                          and category == 'CONTACTOR'
                          and re.fullmatch(r'AX\d+-\d+-\d+', code)
                          and (row.get('specifications') or {}).get('Mã thân') == code
                          and re.match(re.escape(code)+r'-\d+(?=\s|$)', label))
        reviewed_family_match = bool(known_brand
            and (row.get('specifications') or {}).get('Họ thiết bị') == code
            and ((canonical_brand(brand) == 'Shihlin' and category == 'MCCB'
                  and re.fullmatch(r'BM\d+', code) and re.match(re.escape(code)+r'-[A-Z]', label))
                 or (canonical_brand(brand) == 'Mikro' and category in {'PHASE_RELAY', 'VOLTAGE_RELAY', 'POWER_FACTOR_CONTROLLER'}
                     and re.fullmatch(r'(?:MX|PFR)\d+[A-Z]*', code) and re.match(re.escape(code)+r'-', label))))
        if selected_id:
            if public_id(row) != selected_id or not exact:
                continue
        elif code and not (exact or model_match or family_match or body_match or reviewed_family_match):
            continue
        if any(value and (not _values(row,field) or not any(abs(float(value)-v)<0.001 for v in _values(row,field)))
               for field,value in [('poles',device.get('poles')),('current',device.get('in_a'))]):
            continue
        source_spec = str(device.get('spec') or '')
        row_text = ' '.join([label,sku,*[str(v) for v in (row.get('specifications') or {}).values()]])
        requirements = [(number.replace(',', '.'),unit.upper()) for number,unit in re.findall(r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*(mA|V|Hz)\b',source_spec,re.I)]
        published = {(number.replace(',', '.'),unit.upper()) for number,unit in re.findall(r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*(mA|V|Hz)(?:AC|DC)?\b',row_text,re.I)}
        if any(required not in published for required in requirements):
            continue
        if device.get('icu_ka') and (not _values(row,'icu') or min(_values(row,'icu')) < float(device['icu_ka'])):
            continue
        # A frame name needs its electrical configuration; a complete SKU can identify one row.
        automatic = known_brand and bool(code) and (exact or (model_match and device.get('poles') and device.get('in_a')))
        matches.append((row, automatic))
    matched = len(matches)==1 and bool(matches[0][1])
    options = load_price_options()
    choices = []
    for row, _ in matches[:candidate_limit]:
        choices.append({'price_row_id':public_id(row), 'catalog_id':public_id(row),
                        'sku':row.get('sku') or row['item_name'], 'name':row['item_name'],
                        'brand':row['brand'], 'price':row['price'], 'price_source':'published_pricebook',
                        'specifications':row.get('specifications') or {}, 'auto_selectable':matched,
                        'equipment_catalog_id':row.get('equipment_catalog_id'),
                        'cad_price_option_id':options.get(row['id']),
                        'vat_status':row.get('vat_status'), 'effective_date':row.get('effective_date'),
                        'reason':'Dòng giá đã công bố; đối chiếu mã và cấu hình thiết bị.'})
    return {'status':'matched' if matched else 'needs_selection' if matches else 'not_found',
            'price_row_id':public_id(matches[0][0]) if matched else None,
            'row':choices[0] if matched else None, 'candidate_count':len(matches), 'candidates':choices,
            'note':'Đã liên kết dòng bảng giá.' if matched else 'Cần chọn mã và cấu hình trong bảng giá.' if matches else 'Chưa có dòng giá phù hợp; cần bổ sung mã hoặc dữ liệu giá.'}


def link_devices(devices, rows=None):
    rows = published_rows() if rows is None else rows
    for device in devices:
        data = device if isinstance(device,dict) else device.model_dump()
        match = match_device(data, rows)
        grouped = dict(data.get('catalog_candidates') or {})
        for choice in match['candidates']:
            bucket = grouped.setdefault(choice['brand'], [])
            if not any(c.get('price_row_id')==choice['price_row_id'] for c in bucket):
                bucket.insert(0,choice)
        updates = {'pricebook_match':match, 'catalog_candidates':grouped}
        if isinstance(device,dict):
            device.update(updates)
        else:
            for key,value in updates.items():
                setattr(device,key,value)
        accessories = data.get('accompanying_accessories') or []
        for accessory in accessories:
            if isinstance(accessory,dict):
                link_devices([accessory],rows)
        if accessories and not isinstance(device,dict):
            device.accompanying_accessories = accessories
    return devices

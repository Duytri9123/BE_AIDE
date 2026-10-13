"""Commercial configuration matches for a named CAD; never geometry approval."""
import re
from threading import Lock
from app.services.ai.takeoff_pricebook import match_device, public_id

_index_lock = Lock()
_index_devices = None
_index_prices = None
_index_links = {}


def configuration_links(device, rows):
    if not device or device.get('brand_identification_status') != 'verified':
        return {}
    codes = (device.get('ai_identification') or {}).get('cac_ma_dong_san_pham') or []
    product_code = str(device.get('product_code') or '').strip()
    if product_code:
        parts = re.split(r'\s+/\s+', product_code)
        prefix = re.match(r'^([^\d]+)\d', parts[0])
        expanded = [prefix[1]+part if prefix and re.match(r'^\d',part) else part for part in parts]
        codes = [*codes, *expanded]
    if not codes:
        return {}
    spec = device.get('spec') or {}
    poles_match = re.fullmatch(r'(\d+)(?:P)?', str(spec.get('so_cuc') or spec.get('so_cuc_chinh') or ''), re.I)
    kind = str(device.get('type') or '').upper().replace(' ', '_')
    kind = {'PILOTLAMP':'LIGHT','THERMALRELAY':'THERMAL_RELAY','PUSHBUTTON':'PUSHBUTTON'}.get(kind,kind)
    if kind in {'MCB','MCCB','ACB','RCCB','RCBO'} and not poles_match:
        return {}
    selected_current = spec.get('dong_dinh_muc_da_chon')
    criteria = {'category':kind, 'brand':device.get('brand'),
                'poles':int(poles_match[1]) if poles_match else None,
                'in_a':selected_current if isinstance(selected_current,(int,float)) else None}
    identities = set()
    for code in set(codes):
        if not isinstance(code,str) or not code.strip():
            continue
        result = match_device({**criteria,'part_number':code},rows,candidate_limit=None)
        identities.update(c['price_row_id'] for c in result['candidates'])
    return {row['id']:device['id'] for row in rows if public_id(row) in identities}


def device_configuration_links(equipment_id):
    from app.services.catalogtb_browser import browser_data
    from app.services.ai.takeoff_pricebook import published_rows
    global _index_devices, _index_prices, _index_links
    devices, prices = browser_data()['items'], published_rows()
    with _index_lock:
        if devices is not _index_devices or prices is not _index_prices:
            _index_devices, _index_prices, _index_links = devices, prices, {}
        if equipment_id not in _index_links:
            device = next((d for d in devices if d['id']==equipment_id),None)
            if device is None:
                return {}
            _index_links[equipment_id] = configuration_links(device,prices)
        return dict(_index_links[equipment_id])

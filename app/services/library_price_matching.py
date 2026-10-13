"""Commercial configuration matches for a named CAD; never geometry approval."""
import re
from app.services.ai.takeoff_pricebook import match_device, public_id


def configuration_links(device, rows):
    if not device or device.get('brand_identification_status') != 'verified':
        return {}
    codes = (device.get('ai_identification') or {}).get('cac_ma_dong_san_pham') or []
    product_code = str(device.get('product_code') or '').strip()
    if product_code and '/' not in product_code:
        codes = [*codes, product_code]
    if not codes:
        return {}
    spec = device.get('spec') or {}
    poles_match = re.fullmatch(r'(\d+)P', str(spec.get('so_cuc') or ''), re.I)
    kind = str(device.get('type') or '').upper()
    if kind in {'MCB','MCCB','ACB','RCCB','RCBO'} and not poles_match:
        return {}
    selected_current = spec.get('dong_dinh_muc_da_chon')
    criteria = {'category':kind, 'brand':device.get('brand'),
                'poles':int(poles_match[1]) if poles_match else None,
                'in_a':selected_current if isinstance(selected_current,(int,float)) else None}
    identities = set()
    for code in set(codes):
        if not isinstance(code,str) or not code.strip() or '/' in code:
            continue
        result = match_device({**criteria,'part_number':code},rows,candidate_limit=None)
        identities.update(c['price_row_id'] for c in result['candidates'])
    return {row['id']:device['id'] for row in rows if public_id(row) in identities}


def device_configuration_links(equipment_id):
    from app.services.catalogtb_browser import browser_data
    from app.services.ai.takeoff_pricebook import published_rows
    device = next((d for d in browser_data()['items'] if d['id']==equipment_id),None)
    return configuration_links(device,published_rows()) if device else {}

"""Catalog choices for engineering accessory roles; selection stays explicit."""
import re
import unicodedata
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.takeoff_pricebook import match_device

ROLES = {
    'CONTROL_PROTECTION': {'MCB', 'FUSE'}, 'CONTROL_POWER_SUPPLY': {'POWER_SUPPLY', 'TRANSFORMER'},
    'RUN_INDICATOR': {'LIGHT'}, 'FAULT_INDICATOR': {'LIGHT'},
    'MECHANICAL_INTERLOCK': {'INTERLOCK'}, 'ATS_INTERLOCK': {'INTERLOCK'},
    'BYPASS_CONTACTOR': {'CONTACTOR'}, 'SOURCE_MONITOR': {'PHASE_RELAY', 'VOLTAGE_RELAY'},
    'DRIVE_FILTER': {'FILTER'},
    'OVERLOAD_PROTECTION': {'THERMAL_RELAY', 'MOTOR_PROTECTION'},
    'PUSH_BUTTON_ON': {'PUSHBUTTON'}, 'PUSH_BUTTON_OFF': {'PUSHBUTTON'},
    'PUSH_BUTTON_FORWARD': {'PUSHBUTTON'}, 'PUSH_BUTTON_REVERSE': {'PUSHBUTTON'},
    'SELECTOR_SWITCH_3_POSITION': {'SELECTOR_SWITCH'}, 'VFD': {'VFD', 'INVERTER'},
}
KEYWORDS = {
    'AUX_CONTACT': r'tiep diem phu|auxiliary contact',
    'COIL_SUPPRESSOR': r'dap xung|surge suppress|varistor|snubber',
    'STAR_DELTA_WIRING_KIT': r'sao.?tam giac|star.?delta',
    'EMC_TERMINATION': r'emc|shield|man chan',
    'SPEED_POTENTIOMETER': r'bien tro|potentiometer',
    'TERMINAL_BLOCK': r'cau dau|terminal block',
}


def accessory_catalog_options(accessory, brand, rows):
    category = str(accessory.get('category') or '').upper()
    categories = ROLES.get(category, {category})
    filtered = []
    for row in rows:
        if brand and canonical_brand(row.get('brand')) != canonical_brand(brand):
            continue
        text = ' '.join(str(row.get(k) or '') for k in ('item_name', 'group', 'sku'))
        text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
        text = ''.join(c for c in text if not unicodedata.combining(c))
        direct = row.get('category') in categories
        keyword = row.get('category') == 'ACCESSORY' and category in KEYWORDS and re.search(KEYWORDS[category], text)
        if direct or keyword:
            filtered.append(row)
    # Match each actual catalog category without treating a reference as a
    # verified compatible accessory for a particular contactor frame.
    choices = []
    for actual in sorted({r['category'] for r in filtered}):
        trial = {**accessory, 'category': actual, 'brand': brand, 'part_number': '', 'sku': '',
                 'selected_product': None, 'pricebook_match': None}
        match = match_device(trial, [r for r in filtered if r['category'] == actual], candidate_limit=100)
        choices.extend({**c, 'category': actual, 'auto_selectable': False,
                        'match_kind': 'accessory_reference',
                        'reason': 'Mã tham khảo trong bảng giá; kiểm tra điều kiện và tương thích của cụm trước khi sử dụng.'}
                       for c in match['candidates'])
    return choices

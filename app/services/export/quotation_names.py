"""Quotation-only display names; never assign a manufacturer to source devices."""
from copy import deepcopy
import re
import unicodedata
from app.services.library_review_scope import MAIN_DEVICE_TYPES, DEPENDENT_ACCESSORY_TYPES

AUXILIARY_TYPES = {'LIGHT','INDICATOR','PILOT_LIGHT','VOLTMETER','AMMETER','METER','SELECTOR',
    'FUSE','FUSE_HOLDER','TERMINAL','TERMINAL_BLOCK','PUSH_BUTTON','PUSHBUTTON','SWITCH',
    'WIRE','CABLE','DIN_RAIL','DUCT','FAN','FILTER','SOCKET','ENCLOSURE'}

def quotation_name(item):
    name = str(item.get('name') or '')
    kind = str(item.get('category') or item.get('type') or '').upper().replace(' ', '_')
    if kind in MAIN_DEVICE_TYPES | DEPENDENT_ACCESSORY_TYPES or item.get('requires_same_brand'):
        return name
    explicit = [item.get(k) for k in ('brand','detected_brand','manufacturer','part_number','sku')]
    unknown = {'','asian','asia','oem','chưa xác định','—','-','---'}
    if any(str(v or '').strip().casefold() not in unknown for v in explicit):
        return name
    origin = str(item.get('origin') or '').strip().casefold()
    if origin not in unknown | {'vn','việt nam','vietnam','china','trung quốc','france','pháp'}:
        return name
    plain = ''.join(c for c in unicodedata.normalize('NFD', name.lower().replace('đ','d')) if not unicodedata.combining(c))
    if re.search(r'\basian\b',plain):
        return name
    # Historical quotation rows may lack category. Only recognize auxiliary names.
    if not kind:
        if re.search(r'\b(?:mccb|mcb|acb|rcbo|rccb|contactor|shunt|relay|aptomat)\b',plain):
            return name
        auxiliary = any(term in plain for term in ('den bao','cau chi','von ke','ampe ke','chuyen mach',
            'nut nhan','cau dau','mang day','day dien','quat lam mat','o cam'))
    else:
        auxiliary = kind in AUXILIARY_TYPES
    return name + ' Asian' if auxiliary else name

def quotation_display_rows(rows):
    result = deepcopy(rows)
    from app.services.ai.procurement_review import compact_commercial_sections
    result = compact_commercial_sections(result)
    for row in result:
        if row.get('row_type') in ('item','accessory'):
            if row.get('commercial_display'):
                continue
            row['name'] = quotation_name(row)
            if 'asian' in row['name'].casefold() and str(row.get('origin') or '').casefold() in {'asian','asia','oem'}:
                row['origin'] = ''
    return result

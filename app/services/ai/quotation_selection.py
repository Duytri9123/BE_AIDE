"""Select commercial products independently of the recorded drawing identity."""
from copy import deepcopy
import re

from app.core.config import settings
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.takeoff_pricebook import _values, match_device, published_rows
from app.services.library_review_scope import MAIN_DEVICE_TYPES


def replacement_candidates(device, rows):
    """Offer a catalog variant for review while keeping the circuit rating intact."""
    if str(device.get('category')).upper() != 'MCB' or device.get('in_a') != 30:
        return []
    if not device.get('poles') or not device.get('icu_ka'):
        return []
    spec = str(device.get('spec') or '')
    proposed_spec = re.sub(r'(?<![\w./])30\s*A\b', '32A', spec, count=1, flags=re.I)
    if not proposed_spec or proposed_spec == spec:
        return []
    pole_config = re.search(r'([1-4])\s*P\s*\+\s*N', spec, re.I)
    curve = re.search(r'\b(?:curve|courbe|đặc tuyến)\s*([BCD])\b', spec, re.I)
    rows = [row for row in rows if row.get('category') == 'MCB'
            and _values(row, 'current') == [32]
            and min(_values(row, 'icu'), default=0) == device['icu_ka']
            and (not curve or re.search(rf'\b{curve[1]}(?:32\b|\b)', ' '.join(
                [str(row.get('item_name') or ''), *map(str, (row.get('specifications') or {}).values())]), re.I))]
    trial = {**device, 'spec': proposed_spec, 'in_a': 32, 'part_number': '', 'sku': '',
             'pole_configuration': device.get('pole_configuration') or (f'{pole_config[1]}P+N' if pole_config else None),
             'selected_product': None}
    return [{**row, 'proposed_spec': proposed_spec, 'auto_selectable': False,
             'match_kind': 'conditional_alternative', 'requires_confirmation': True,
             'reason': 'Đề xuất 30A => 32A. Cần xác nhận dây dẫn, tải và phối hợp bảo vệ.'}
            for row in match_device(trial, rows)['candidates']]


def select_quotation_devices(devices, preferred_brand=None, rows=None):
    """Use one maker for main equipment and validate each SKU against published facts.

    Explicit row selections survive. A missing product never triggers a different
    manufacturer or a reused price from the drawing's original model.
    """
    brand = preferred_brand
    explicit_brand = bool(brand and str(brand).strip().casefold() not in
                          {'theo thiết kế', 'theo thiet ke', 'gốc', 'all', 'auto', 'default'})
    if not explicit_brand:
        brand = settings.DEFAULT_BRAND
    brand = canonical_brand(brand)
    rows = published_rows() if rows is None else rows
    maker_rows = [row for row in rows if canonical_brand(row.get('brand')) == brand]
    result = deepcopy(devices)
    for device in result:
        kind = str(device.get('category') or '').upper()
        if kind not in MAIN_DEVICE_TYPES:
            continue
        same_brand = canonical_brand(device.get('brand') or device.get('detected_brand') or '') == brand
        if device.get('selection_source') == 'approved_quotation' or (
                device.get('selection_source') == 'user_selected' and (same_brand or not explicit_brand)):
            continue
        original = {key: device.get(key) for key in ('brand', 'detected_brand', 'part_number', 'spec')}
        observations = device.setdefault('source_observations', {}) or {}
        device['source_observations'] = observations
        observations.setdefault('quotation_source_identity', original)
        observations.pop('quotation_replacement', None)
        for key, pattern in (
            ('poles', r'(?<!\w)([1-4])\s*P\b'),
            ('in_a', r'(?<![\w./])(\d+(?:[.,]\d+)?)\s*A\b'),
            ('icu_ka', r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*k\s*A\b'),
        ):
            if device.get(key) is None and (value := re.search(pattern, str(device.get('spec') or ''), re.I)):
                device[key] = float(value[1].replace(',', '.'))
        device.update(brand=brand, detected_brand='', selection_source='default_brand', selected_product=None,
                      pricebook_match=None, unit_price=None, price=None)
        if not same_brand:
            device.update(part_number='', sku='', catalog_matches={})
        match = match_device(device, maker_rows)
        if not match['candidates'] and (device.get('part_number') or device.get('sku')):
            # Search equivalent products of the same maker using circuit ratings.
            device['part_number'] = ''
            device['sku'] = ''
            match = match_device(device, maker_rows)
        candidates = match['candidates']
        if explicit_brand and not candidates:
            candidates = replacement_candidates(device, maker_rows)
            if candidates:
                observations['quotation_replacement'] = candidates[0]
        device['catalog_candidates'] = {brand: candidates} if candidates else {}
        device['pricebook_match'] = match
        for candidate in match['candidates']:
            trial = {**device, 'part_number': candidate['sku']}
            verified = match_device(trial, maker_rows)
            if verified['status'] != 'matched':
                continue
            if kind in {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB'} and not all(
                    device.get(key) for key in ('poles', 'in_a', 'icu_ka')):
                continue
            device.update(part_number=candidate['sku'], selected_product=candidate,
                          pricebook_match=verified, selection_source='default_brand')
            break
    return result

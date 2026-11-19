"""Select commercial products independently of the recorded drawing identity."""
from copy import deepcopy
import re

from app.core.config import settings
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.takeoff_pricebook import match_device, published_rows
from app.services.library_review_scope import MAIN_DEVICE_TYPES


def select_quotation_devices(devices, preferred_brand=None, rows=None):
    """Use one maker for main equipment and validate each SKU against published facts.

    Explicit row selections survive. A missing product never triggers a different
    manufacturer or a reused price from the drawing's original model.
    """
    brand = preferred_brand
    if not brand or str(brand).casefold() in {'theo thiết kế', 'gốc', 'all', 'auto', 'default'}:
        brand = settings.DEFAULT_BRAND
    brand = canonical_brand(brand)
    rows = published_rows() if rows is None else rows
    result = deepcopy(devices)
    for device in result:
        kind = str(device.get('category') or '').upper()
        if kind not in MAIN_DEVICE_TYPES or device.get('selection_source') in {'user_selected', 'approved_quotation'}:
            continue
        original = {key: device.get(key) for key in ('brand', 'detected_brand', 'part_number', 'spec')}
        observations = device.setdefault('source_observations', {}) or {}
        device['source_observations'] = observations
        observations.setdefault('quotation_source_identity', original)
        for key, pattern in (
            ('poles', r'(?<!\w)([1-4])\s*P\b'),
            ('in_a', r'(?<![\w./])(\d+(?:[.,]\d+)?)\s*A\b'),
            ('icu_ka', r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*k\s*A\b'),
        ):
            if device.get(key) is None and (value := re.search(pattern, str(device.get('spec') or ''), re.I)):
                device[key] = float(value[1].replace(',', '.'))
        same_brand = canonical_brand(device.get('brand') or device.get('detected_brand') or '') == brand
        device.update(brand=brand, detected_brand='', selection_source='default_brand', selected_product=None,
                      pricebook_match=None, unit_price=None, price=None)
        if not same_brand:
            device['part_number'] = ''
        match = match_device(device, rows)
        if not match['candidates'] and device.get('part_number'):
            # Search equivalent products of the same maker using circuit ratings.
            device['part_number'] = ''
            match = match_device(device, rows)
        candidates = match['candidates']
        device['catalog_candidates'] = {brand: candidates} if candidates else {}
        device['pricebook_match'] = match
        for candidate in candidates:
            trial = {**device, 'part_number': candidate['sku']}
            verified = match_device(trial, rows)
            if verified['status'] != 'matched':
                continue
            if kind in {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB'} and not all(
                    device.get(key) for key in ('poles', 'in_a', 'icu_ka')):
                continue
            device.update(part_number=candidate['sku'], selected_product=candidate,
                          pricebook_match=verified, selection_source='default_brand')
            break
    return result

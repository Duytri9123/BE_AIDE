"""Apply a preferred maker only where the published catalog verifies a replacement."""
from copy import deepcopy

from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.quotation_selection import select_quotation_devices


def compatible_brand_replacements(devices, brand, rows=None):
    proposals = select_quotation_devices(devices, brand, rows)
    result, changed = [], 0
    for original, proposal in zip(devices, proposals):
        match = proposal.get('pricebook_match') or {}
        product = proposal.get('selected_product') or {}
        if (match.get('status') != 'matched' or not product.get('sku')
                or canonical_brand(product.get('brand')) != canonical_brand(brand)):
            result.append(deepcopy(original))
            continue
        if (canonical_brand(original.get('brand')) == canonical_brand(brand)
                and original.get('part_number') == product['sku']):
            result.append(deepcopy(original))
            continue
        proposal['selection_source'] = 'user_request'
        proposal['sku'] = product['sku']
        proposal['unit_price'] = product.get('price')
        proposal['price'] = product.get('price')
        result.append(proposal)
        changed += 1
    return result, changed

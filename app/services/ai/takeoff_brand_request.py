"""Apply an explicit procurement brand during takeoff, preserving source facts."""
from copy import deepcopy
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.library_review_scope import MAIN_DEVICE_TYPES, DEPENDENT_ACCESSORY_TYPES


def requested_brand_applies(device):
    get = device.get if isinstance(device, dict) else lambda key, default=None: getattr(device, key, default)
    kind = str(get('category') or '').upper().replace(' ', '_')
    return kind in MAIN_DEVICE_TYPES | DEPENDENT_ACCESSORY_TYPES or bool(
        get('requires_same_brand', False))


def apply_takeoff_brand(device, brand):
    if not brand or not requested_brand_applies(device):
        return False
    get = device.get if isinstance(device, dict) else lambda key, default=None: getattr(device, key, default)
    def put(key, value):
        if isinstance(device, dict):
            device[key] = value
        else:
            setattr(device, key, value)
    if not (get('selection_source') == 'user_request' and canonical_brand(get('brand')) == canonical_brand(brand)):
        observations = deepcopy(get('source_observations') or {})
        observations.setdefault('schematic', {
            'brand': get('detected_brand') or get('brand') or '',
            'part_number': get('part_number') or get('sku') or '', 'spec': get('spec'),
            'category': get('category'), 'quantity': get('quantity'),
        })
        put('source_observations', observations)
        put('detected_brand', observations['schematic'].get('brand') or '')
        if canonical_brand(get('brand') or '') != canonical_brand(brand):
            for field, value in (('part_number', ''), ('selected_product', None),
                                 ('pricebook_match', None), ('catalog_matches', {})):
                put(field, value)
            if isinstance(device, dict):
                device['sku'] = ''
        put('brand', brand)
        put('selection_source', 'user_request')
        put('suggested_brands', [brand])
        put('technical_match_note',
            f'Áp dụng yêu cầu {brand} ngay khi bóc tách; đối chiếu sản phẩm theo thông số nguồn. '
            'Chưa xác nhận mã hàng khi chưa đủ cấu hình kỹ thuật.')
    for accessory in get('accompanying_accessories') or []:
        if isinstance(accessory, dict) and requested_brand_applies(accessory):
            apply_takeoff_brand(accessory, brand)
    return True


def requested_brand_candidates(candidates, brand):
    return {maker: rows for maker, rows in (candidates or {}).items()
            if canonical_brand(maker) == canonical_brand(brand)}

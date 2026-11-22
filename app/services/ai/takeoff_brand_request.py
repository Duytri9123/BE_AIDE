"""Apply a procurement brand only when a compatible product is verified."""
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.library_review_scope import MAIN_DEVICE_TYPES


def requested_brand_applies(device):
    get = device.get if isinstance(device, dict) else lambda key, default=None: getattr(device, key, default)
    kind = str(get('category') or '').upper().replace(' ', '_')
    return kind in MAIN_DEVICE_TYPES


def apply_takeoff_brand(device, brand):
    if not brand or not requested_brand_applies(device):
        return False
    from app.services.ai.compatible_brand_selection import compatible_brand_replacements
    data = device if isinstance(device, dict) else device.model_dump()
    replacements, changed = compatible_brand_replacements([data], brand)
    if not changed:
        return False
    updated = replacements[0]
    if isinstance(device, dict):
        device.update(updated)
    else:
        for key, value in updated.items():
            if key in type(device).model_fields:
                setattr(device, key, value)
    return True



def requested_brand_candidates(candidates, brand):
    return {maker: rows for maker, rows in (candidates or {}).items()
            if canonical_brand(maker) == canonical_brand(brand)}

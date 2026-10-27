"""User-requested takeoff priority; optional prices are never invented."""

# Loại hình CAD dạng mẫu/generic — không có hãng xác định, không cần khớp giá chính xác.
_GENERIC_SHAPE_TYPES = {
    'TERMINAL_BLOCK', 'TERMINAL', 'ACCESSORY', 'AUX_CONTACT', 'AUX_CONTACTS',
    'INTERLOCK', 'MOUNTING_TEMPLATE', 'ASSEMBLY_REFERENCE',
    # Phụ kiện cơ khí tủ điện
    'CABLE_DUCT', 'BUSBAR_SUPPORT', 'DOOR_INTERLOCK', 'MOUNTING_SUPPORT',
    # Ổn áp dạng mẫu (chưa xác định hãng)
    'VOLTAGE_STABILIZER',
}

# Danh mục thư mục không yêu cầu giá chính xác
_OPTIONAL_CATEGORIES = {
    'Cầu đấu', 'Khóa', 'Phíp', 'Phụ kiện tủ điện', 'Đố', 'Đồng',
    'Ổ cắm', 'Form tủ', 'Quạt',
}


def exact_price_required(device):
    kind = str(device.get('type') or device.get('category') or '').upper().replace(' ', '_')
    if device.get('brand_identification_status') == 'not_applicable':
        return False
    if device.get('category') in _OPTIONAL_CATEGORIES:
        return False
    if kind in _GENERIC_SHAPE_TYPES or 'CẦU_ĐẤU' in kind:
        return False
    # CAD dạng mẫu (generic_shape): không yêu cầu giá — chỉ dùng để vẽ bố trí tủ
    ai = device.get('nhan_dien_ai') or device.get('ai_identification') or {}
    if ai.get('generic_shape'):
        return False
    return True


MAIN_DEVICE_TYPES = {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB', 'ISOLATOR',
                     'CONTACTOR', 'THERMAL_RELAY', 'VFD', 'INVERTER', 'ATS'}
DEPENDENT_ACCESSORY_TYPES = {'SHUNT_TRIP', 'UNDERVOLTAGE_RELEASE', 'AUX_CONTACT',
                            'AUX_CONTACTS', 'INTERLOCK'}


def preferred_brand_for_device(device, preferred_brand=None):
    """Project brand preferences concern main devices; retain explicit identities."""
    get = device.get if isinstance(device, dict) else lambda key, default=None: getattr(device, key, default)
    kind = str(get('category') or get('type') or '').upper().replace(' ', '_')
    if get('selection_source') == 'user_request' and get('brand') and (
            kind in MAIN_DEVICE_TYPES | DEPENDENT_ACCESSORY_TYPES or get('requires_same_brand')):
        return get('brand')
    explicit = get('detected_brand') or (get('brand') if get('selection_source') not in
                                       {'default_brand', 'unspecified_brand'} else None)
    if explicit and str(explicit).strip().casefold() not in {'asian', 'asia', 'oem'}:
        return explicit
    kind = str(get('category') or get('type') or '').upper().replace(' ', '_')
    if kind in MAIN_DEVICE_TYPES or kind in DEPENDENT_ACCESSORY_TYPES or get('requires_same_brand'):
        return preferred_brand
    return None

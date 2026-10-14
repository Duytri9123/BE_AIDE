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

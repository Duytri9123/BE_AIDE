"""Read per-face clearances from reviewed source evidence, not sheet margins."""
import math


# Margin mặc định (mm) dùng khi placement_rules chưa được xác minh nhưng
# clean_bounds đã có. Chỉ dùng cho bố trí sơ bộ; không phải mép chế tạo.
_DEFAULT_MARGIN = {
    'mounting_plate': {'left_mm': 30, 'bottom_mm': 40, 'right_mm': 30, 'top_mm': 50},
    'inner_door':     {'left_mm': 25, 'bottom_mm': 30, 'right_mm': 25, 'top_mm': 40},
    'outer_door':     {'left_mm': 20, 'bottom_mm': 25, 'right_mm': 20, 'top_mm': 35},
}


def reference_region(bounds, source_item, face):
    """Proposed inset for a review drawing; never marks source rules verified."""
    try:
        return usable_region(bounds, source_item, face)
    except ValueError:
        left, bottom, right, top = bounds
        # Dùng margin chuẩn kỹ thuật thay vì 40mm cứng cho mọi mặt
        m = _DEFAULT_MARGIN.get(face, {'left_mm': 40, 'bottom_mm': 40, 'right_mm': 40, 'top_mm': 40})
        region = (left + m['left_mm'], bottom + m['bottom_mm'],
                  right - m['right_mm'], top - m['top_mm'])
        if region[0] >= region[2] or region[1] >= region[3]:
            raise ValueError('Mặt tủ không đủ vùng bố trí nháp: ' + face)
        return region


def usable_region(bounds, source_item, face):
    rule = ((source_item or {}).get('placement_rules') or {}).get(face) or {}
    if rule.get('verified') is not True or not rule.get('source_handles'):
        # Fallback: nếu form có clean_bounds xác nhận + kích thước hợp lý,
        # dùng margin mặc định theo ngành thay vì lỗi hoàn toàn.
        # Vẫn đánh dấu là sơ bộ (reference) chứ không phải verified.
        left, bottom, right, top = bounds
        face_w, face_h = right - left, top - bottom
        if face_w > 100 and face_h > 100:
            m = _DEFAULT_MARGIN.get(face, {'left_mm': 40, 'bottom_mm': 40, 'right_mm': 40, 'top_mm': 40})
            region = (left + m['left_mm'], bottom + m['bottom_mm'],
                      right - m['right_mm'], top - m['top_mm'])
            if region[0] < region[2] and region[1] < region[3]:
                # Trả về vùng sơ bộ; caller biết đây là reference vì không có verified rule
                return region
        raise ValueError('Chưa xác nhận mép lắp đặt, hèm và khoảng dây cho mặt ' + face)
    values = [rule.get(key) for key in ('left_mm', 'bottom_mm', 'right_mm', 'top_mm')]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Khoảng chừa mép có dữ liệu không hợp lệ: ' + face)
    left, bottom, right, top = bounds
    l, b, r, t = values
    region = (left + l, bottom + b, right - r, top - t)
    if region[0] >= region[2] or region[1] >= region[3]:
        raise ValueError('Khoảng chừa mép làm hết vùng lắp thiết bị: ' + face)
    return region


def device_gap(device, axis):
    rule = device.get('verified_placement_clearance') or {}
    if rule.get('verified') is True and rule.get('source_reference'):
        value = rule.get(axis + '_mm')
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            return value
    # DIN modular adjacency is a layout convention only; thermal and terminal
    # checks remain separate release checks.
    if axis == 'horizontal' and str(device.get('category') or '').upper() in ('MCB', 'RCBO', 'RCCB'):
        return 0
    # Fallback kỹ thuật theo loại thiết bị và trục
    cat = str(device.get('category') or '').upper()
    if axis == 'vertical':
        if cat in ('ACB', 'MCCB'):
            return 60
        if cat in ('CONTACTOR', 'TIMER', 'RELAY'):
            return 30
        return 40
    # horizontal
    if cat in ('ACB', 'MCCB'):
        return 30
    return 15

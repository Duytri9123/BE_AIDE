"""Only installation data backed by a model-specific source can drive automatic layout."""
import math

SIDES = ('left', 'right', 'top', 'bottom', 'front', 'rear')

def mounting_profile(model):
    params = model.parameters or {}
    dimensions = model.dimensions or {}
    supplied = params.get('mounting_profile') or {}
    gaps = supplied.get('clearances_mm') or {}
    finite = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    complete_dims = all(finite(dimensions.get(k)) and dimensions[k] > 0 for k in ('w', 'h', 'd'))
    complete_gaps = all(finite(gaps.get(k)) and gaps[k] >= 0 for k in SIDES)
    missing = []
    if not complete_dims: missing.append('Kích thước rộng, cao, sâu')
    if not supplied.get('dimensions_verified'): missing.append('Xác nhận kích thước đúng model và đơn vị mm')
    if not complete_gaps: missing.append('Khoảng hở lắp đặt từng phía')
    if not supplied.get('wiring_verified'): missing.append('Vùng đấu dây và bán kính uốn cáp')
    if not supplied.get('thermal_verified'): missing.append('Điều kiện tản nhiệt và hướng lắp')
    if not supplied.get('source'): missing.append('Tài liệu lắp đặt theo model')
    return dict(ready_for_layout=not missing, missing=missing, dimensions_mm={k:dimensions.get(k) for k in ('w','h','d')},
                clearances_mm={k:gaps.get(k) for k in SIDES}, source=supplied.get('source'))

"""Choose a complete original form that can hold the selected review geometry."""
from app.services.cad.catalogtb_assets import resolve, instance_count
from app.services.cad import cabinet_templates
from app.services.cad.design_policy import dimensions_for_current
import json
from app.services.cad.design_policy import RULES_PATH


def fit_vertical_review(devices, dimensions):
    if not any((d.get('cad') or {}).get('branch_arrangement') == 'two_vertical_banks' for d in devices):
        return dimensions
    incoming, branches = [], []
    for d in devices:
        asset = resolve((d.get('cad') or {})['asset_id'], 'front')
        from app.services.cad.device_envelope import _bounds
        bound_width,bound_height = _bounds(asset)
        category = d.get('category')
        if category in ('MCCB','ACB'):
            incoming.append((d,bound_width,bound_height))
        elif category in ('MCB','RCBO','RCCB'):
            branches.extend((bound_height,bound_width) for _ in range(instance_count(d.get('quantity',1),asset)))
    if not incoming or not branches:
        return dimensions
    from app.services.cad.design_labels import rating_text
    current = max(float(rating_text(d)[:-1]) if rating_text(d) else 0 for d,_,_ in incoming)
    policy = dimensions_for_current(current)
    variables=json.loads(RULES_PATH.read_text(encoding='utf8'))['design_variables']
    heights, widths = [0.,0.], [0.,0.]
    for width,height in sorted(branches,key=lambda pair: -pair[0]*pair[1]):
        bank = min(range(2),key=lambda i:heights[i])
        heights[bank] += height
        widths[bank] = max(widths[bank],width)
    required = {
        'height': max(float(dimensions[0]), (policy['top_gap_mm'] or 150) + max(h for _,_,h in incoming) + variables.get('d15',50) + max(heights) + variables.get('d16',160)),
        'width': max(float(dimensions[1]),2*(policy['side_margin_mm'] or 110)+sum(widths)+160),
        'depth': float(dimensions[2]),
    }
    fitting = []
    for form in cabinet_templates.inventory():
        size = form.get('dimensions') or {}
        faces = {face.get('kind'): face['clean_bounds'] for face in form.get('faces',[]) if face.get('clean_bounds')}
        complete = {'outer_door','inner_door','mounting_plate'} <= faces.keys()
        aligned = complete and all(abs(faces[k][2]-faces[k][0]-size.get('width',0)) <= 1 and abs(faces[k][3]-faces[k][1]-size.get('height',0)) <= 1 for k in ('inner_door','mounting_plate')) and abs(faces['inner_door'][1]-faces['mounting_plate'][1]) <= 1
        if form.get('kind') == 'indoor' and aligned and all(size.get(axis,0) >= required[axis] for axis in required):
            fitting.append(form)
    if not fitting:
        raise ValueError(f"Không có form nguồn đủ vùng xương cá: cần tối thiểu H{required['height']:.0f}×W{required['width']:.0f}×D{required['depth']:.0f} mm.")
    selected = min(fitting,key=lambda f:f['dimensions']['height']*f['dimensions']['width']*f['dimensions']['depth'])['dimensions']
    return tuple(selected[axis] for axis in ('height','width','depth'))

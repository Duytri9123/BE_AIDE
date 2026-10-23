"""A physical expansion zone, separate from wiring and mounting clearances."""
import math
from app.core.config import settings

LAYER = 'AIDE_RESERVED_SPACE'


def fraction():
    return float(settings.ENCLOSURE_RESERVE_SPACE_PCT) / 100


def sizing_height(occupied_height):
    # The percentage is a fraction of the resulting usable space, not a
    # percentage merely added to the equipment footprint.
    return math.ceil(float(occupied_height) / (1 - fraction()))


def allocate(bounds):
    left, bottom, right, top = map(float, bounds)
    height = (top - bottom) * fraction()
    return (left, bottom + height, right, top), {
        'policy': 'dedicated_mounting_plate_expansion_zone',
        'basis': 'system_design_policy_not_a_standard_requirement',
        'requested_pct': fraction() * 100,
        'bounds_mm': [left, bottom, right, bottom + height],
        'usable_area_mm2': (right - left) * (top - bottom),
        'reserved_area_mm2': (right - left) * height,
    }


def draw(msp, reservation):
    if reservation['reserved_area_mm2'] <= 0:
        return
    if LAYER not in msp.doc.layers:
        msp.doc.layers.new(LAYER, dxfattribs={'color': 3})
    l, b, r, t = reservation['bounds_mm']
    msp.add_lwpolyline([(l,b),(r,b),(r,t),(l,t)], close=True, dxfattribs={'layer': LAYER})
    msp.add_text(f"DU PHONG {reservation['requested_pct']:g}% - KHONG LAP THIET BI",
                 dxfattribs={'layer': LAYER, 'height': min(8, max(1, (r-l)/70)),
                             'insert': (l+2,b+2)})


def check(reservation, placements):
    l,b,r,t = reservation['bounds_mm']
    overlaps = []
    for p in placements:
        if (p.get('mounting_face') or p.get('face') or 'mounting_plate') != 'mounting_plate':
            continue
        x,y = p['x'],p['y']
        w,h = p.get('width',p.get('w',0)),p.get('height',p.get('h',0))
        if min(x+w,r)-max(x,l)>1e-6 and min(y+h,t)-max(y,b)>1e-6:
            overlaps.append(p.get('tag') or '?')
    if overlaps:
        raise ValueError('Thiết bị chiếm vùng dự phòng: '+', '.join(overlaps))
    return {**reservation, 'status': 'verified_empty', 'overlapping_devices': []}


def from_dxf(doc, placements):
    outlines=list(doc.modelspace().query(f'LWPOLYLINE[layer=="{LAYER}"]'))
    if not outlines:
        return {'status': 'not_requested' if fraction()==0 else 'not_verified'}
    points=list(outlines[0].get_points('xy'))
    l,b=min(p[0] for p in points),min(p[1] for p in points)
    r,t=max(p[0] for p in points),max(p[1] for p in points)
    area=(r-l)*(t-b)
    return check({'bounds_mm':[l,b,r,t], 'requested_pct':fraction()*100,
                  'reserved_area_mm2':area,'usable_area_mm2':area/fraction(),
                  'policy':'dedicated_mounting_plate_expansion_zone',
                  'basis':'system_design_policy_not_a_standard_requirement'}, placements)

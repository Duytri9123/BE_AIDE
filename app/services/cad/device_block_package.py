"""Shared insertable JSON contract; missing source geometry stays explicitly draft."""
import hashlib
import math

# Editable layout envelopes, never manufacturer dimensions or certified cutouts.
ENVELOPES = {
    'MCB': (54, 85, 75), 'RCCB': (72, 85, 75), 'RCBO': (36, 90, 75),
    'MCCB': (105, 165, 100), 'ACB': (400, 400, 300),
    'CONTACTOR': (55, 85, 90), 'THERMAL_RELAY': (55, 70, 90),
    'PUSHBUTTON': (30, 30, 50), 'LIGHT': (30, 30, 50), 'PILOT_LIGHT': (30, 30, 50),
    'SELECTOR': (30, 40, 60), 'METER': (96, 96, 80), 'TIMER': (45, 70, 70),
    'TERMINAL': (10, 50, 45), 'RELAY': (25, 70, 65), 'POWER_SUPPLY': (60, 100, 100),
    'PLC': (120, 90, 80), 'VFD': (150, 250, 180), 'ACCESSORY': (50, 70, 60),
}


def rectangle(width, height):
    return [[0, 0], [width, 0], [width, height], [0, height], [0, 0]]


def draft_block(product):
    """A draggable placeholder for every commercial row, with no false CAD claim."""
    category = str(product.get('category') or '').upper()
    width, height, depth = ENVELOPES.get(category, (60, 90, 75))
    projections = []
    for face, w, h in [('front', width, height), ('side', depth, height),
                       ('top', width, depth), ('back', width, height),
                       ('bottom', width, depth), ('left', depth, height)]:
        projections.append(dict(face=face, label=face, paths=[rectangle(w, h)], width=w,
                                height=h, units='mm', geometry_status='parametric_unverified'))
    panel = category in {'PUSHBUTTON', 'LIGHT', 'PILOT_LIGHT', 'SELECTOR', 'METER'}
    result = dict(id='draft-'+str(product['id']), price_row_id=str(product['id']), product=product,
                name=product.get('sku') or product.get('name') or product.get('item_name') or 'Thiết bị',
                brand=product.get('brand'), width=width, height=height, depth=depth,
                front=projections[0], side=projections[1], top=projections[2], projections=projections,
                projectionOnly=False, panel_device=panel, geometry_status='parametric_unverified',
                dimensions_verified=False, profile='Bao hình bố trí tham khảo theo nhóm '+category,
                warnings=['Chưa có CAD liên kết: kích thước bao hình tham khảo, cần chỉnh theo mã thực tế.'])
    if panel:
        head = 8
        result['mechanics'] = dict(kind='panel_operator', holeDiameter=22 if category != 'METER' else width-4,
             headDepth=head, rearDepth=depth-head, rearWidth=width-4, rearHeight=height-4,
             source='Bao hình phương án chưa xác nhận kích thước hoặc lỗ khoét theo mã thực tế.')
        if category == 'METER':
            result['mechanics']['headShape'] = 'rectangle'
    return result


def public_row_id(row):
    return hashlib.sha256(row['id'].encode()).hexdigest()[:24]


def block_package(product, candidates):
    native = bool(candidates)
    prepared=[]
    for candidate in candidates:
        front, side = candidate.get('front') or {}, candidate.get('side') or {}
        positive = lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
        height_matches = (positive(front.get('height')) and
                          positive(side.get('height')) and
                          abs(front['height'] - side['height']) <= max(2, front['height'] * .05))
        same_variant = front.get('variant_id') == side.get('variant_id')
        if not positive(candidate.get('depth')) or not height_matches or not same_variant:
            candidate={**candidate, 'depth':0,
                       'projectionOnly':True,
                       'dimensions_verified':False,
                       'warnings':[*candidate.get('warnings',[]),
                                   'Chưa xác nhận chiều sâu theo model; giữ hình chiếu 2D.']}
        prepared.append(candidate)
    return dict(schema_version=2, contract='aide.cad-device-block', units='mm',
                product=product, geometry_status='source_cad' if native else 'parametric_unverified',
                candidates=prepared or [draft_block(product)])

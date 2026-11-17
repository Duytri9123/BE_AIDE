"""Distinguish device bodies, operators and panel openings for every library family.

Category rules propose ownership only. They never supply a hole size, a depth,
or a project door choice. Supplier front/side bounds are not panel cutouts.
"""
import hashlib
import math
import re
from pathlib import Path

BODY_INTERNAL = {'MCCB', 'ACB', 'MCB', 'RCCB', 'RCBO', 'ELCB', 'RCD', 'MPCB',
    'CB', 'MOTOR_PROTECTION', 'CONTACTOR', 'THERMAL_RELAY', 'RELAY', 'PHASE_RELAY',
    'TIMER', 'FUSE', 'FUSE_HOLDER', 'FUSEASSEMBLY', 'SPD', 'VFD', 'SOFT_STARTER',
    'CAPACITOR', 'TRANSFORMER', 'REACTOR', 'POWER_SUPPLY', 'PLC', 'DDC', 'IO_MODULE',
    'TERMINAL_BLOCK', 'TERMINAL_BAR', 'TERMINAL_STOP', 'TERMINAL_END_STOP',
    'VOLTAGE_STABILIZER', 'ISOLATOR', 'SWITCH_DISCONNECTOR'}
PANEL_CANDIDATES = {'METER', 'LIGHT', 'INDICATOR', 'PILOT', 'PUSHBUTTON', 'BUTTON',
    'SELECTOR', 'SELECTOR_SWITCH', 'SELECTOR_METER', 'HMI', 'BUZZER',
    'GENERATOR_CONTROLLER', 'POWER_FACTOR_CONTROLLER'}
HOST_PARTS = {'AUX_CONTACT', 'INTERLOCK', 'ACCESSORY', 'CABLE_LUG', 'BUSBAR_CLAMP',
    'INSULATING_SUPPORT', 'FASTENER', 'CT', 'BUSBAR', 'COPPERBUSBAR'}
CABINET_PARTS = {'FAN', 'FAN_GUARD', 'FILTER', 'VENT_FILTER', 'VENT_HOOD', 'HINGE',
    'CABINET_LOCK', 'CABINET_LATCH', 'CABINET_HANDLE', 'LIFTING_ATTACHMENT',
    'WALL_BRACKET', 'MOUNTING_SUPPORT', 'DOCUMENT_POCKET', 'WIRING_DUCT',
    'LABEL_HOLDER', 'SAFETY_LABEL', 'INSPECTION_WINDOW', 'SOCKET'}


def category_code(value):
    code = re.sub(r'[ -]+', '_', str(value or '').strip()).upper()
    return {'AUXCONTACT': 'AUX_CONTACT', 'THERMALRELAY': 'THERMAL_RELAY',
        'PHASERELAY': 'PHASE_RELAY', 'MOUNTINGSUPPORT': 'MOUNTING_SUPPORT',
        'FUSE_ASSEMBLY': 'FUSEASSEMBLY'}.get(code, code)


def _validated_cutout(profile, profile_path):
    """Require an explicit model-bound installation contract; no bbox fallback."""
    contract = profile.get('verified_installation') or {}
    cutout = contract.get('panel_cutout') or {}
    if not (contract.get('verified') is True and contract.get('model_code') and
            contract.get('variant_id') and cutout.get('verified') is True and
            cutout.get('role') == 'panel_cutout' and cutout.get('units') == 'mm' and
            cutout.get('source_reference') and profile_path):
        return None
    origin = cutout.get('operation_origin_from_front_mm')
    points = cutout.get('points_mm')
    if (not isinstance(origin, list) or len(origin) != 2 or not isinstance(points, list)
            or len(points) < 3 or not all(isinstance(p, list) and len(p) == 2 for p in points)):
        return None
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v)
           for p in [origin, *points] for v in p):
        return None
    if points[0] == points[-1]:
        points = points[:-1]
    if len(points) < 3 or len({tuple(p) for p in points}) != len(points):
        return None
    def orient(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def touches(a, b, c):
        return abs(orient(a,b,c)) < 1e-9 and min(a[0],b[0]) <= c[0] <= max(a[0],b[0]) and min(a[1],b[1]) <= c[1] <= max(a[1],b[1])
    for i, a in enumerate(points):
        b = points[(i+1)%len(points)]
        for j in range(i+1, len(points)):
            if j == i+1 or (i == 0 and j == len(points)-1):
                continue
            c, d = points[j], points[(j+1)%len(points)]
            if (orient(a,b,c)*orient(a,b,d) < 0 and orient(c,d,a)*orient(c,d,b) < 0
                    or touches(a,b,c) or touches(a,b,d) or touches(c,d,a) or touches(c,d,b)):
                return None
    if abs(sum(p[0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*p[1]
               for i,p in enumerate(points))) < .001:
        return None
    parent = Path(profile_path).resolve().parent
    filename = cutout.get('source_file')
    if not isinstance(filename, str):
        return None
    source = (parent / filename).resolve()
    if not source.is_relative_to(parent) or not source.is_file():
        return None
    if hashlib.sha256(source.read_bytes()).hexdigest() != cutout.get('source_sha256'):
        return None
    # A source artifact is evidence for the named model/variant, never its siblings.
    return {**cutout, 'points_mm': points, 'model_code': contract['model_code'], 'variant_id': contract['variant_id']}


def installation_review(profile, profile_path=None, *, category=None, variant_id=None):
    ai = profile.get('nhan_dien_ai') or {}
    kind = category_code(category or ai.get('loai_thiet_bi_code') or profile.get('ban_chat'))
    if kind in BODY_INTERNAL:
        ownership, faces = 'internal_body', ['mounting_plate', 'verified_rail_or_support']
    elif kind in PANEL_CANDIDATES:
        ownership, faces = 'panel_or_internal_variant_review', ['project_selected_panel_or_internal_mount']
    elif kind in HOST_PARTS:
        ownership, faces = 'host_or_support_review', ['verified_host_or_support']
    elif kind in CABINET_PARTS:
        ownership, faces = 'cabinet_part_review', ['project_selected_cabinet_surface']
    else:
        ownership, faces = 'unresolved_or_reference', []
    cutout = _validated_cutout(profile, profile_path)
    if cutout and variant_id is not None and cutout['variant_id'] != variant_id:
        cutout = None
    declared = profile.get('bo_tri_lap_dat') or {}
    return dict(schema_version=1, category=kind, body_ownership=ownership,
        proposed_body_mounts=faces, body_mount_verified=False,
        declared_mounting=declared, project_owner_face=None,
        body_on_door_allowed=False if ownership == 'internal_body' else None,
        operator_is_separate_from_body=kind in {'MCCB', 'ACB', 'MCB', 'RCCB', 'RCBO', 'ELCB', 'ATS', 'ISOLATOR', 'SWITCH_DISCONNECTOR'},
        cutout_requirement='project_and_model_dependent',
        auto_cutout_allowed=cutout is not None, cutout=cutout,
        cutout_status='verified_model_contract' if cutout else 'requires_model_cutout_evidence',
        front_bbox_is_cutout=False, automatic_standoff_allowed=False,
        required_checks=['project_owner_face', 'physical_mounting_datum', 'model_variant',
            'operation_datum', 'cutout_profile', 'door_frame_hinges_lock', 'depth',
            'door_sweep', 'terminal_clearance'], release_ready=False)


def validate_body_face(category, face, component_role='body'):
    """An operating feature on a door does not move the internal device body."""
    if (category_code(category) in BODY_INTERNAL and face in {'inner_door', 'outer_door'}
            and component_role not in {'operating_handle', 'operator', 'escutcheon'}):
        raise ValueError('Thân thiết bị này lắp bên trong; cần tách mặt thao tác khỏi thân trước khi gán lên cánh.')

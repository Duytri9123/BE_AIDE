"""User cabinet layout policy; distinct from verified electrical clearance."""
import json
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[3] / 'data/design_rules/fishbone_rstn.json'

def dimensions_for_current(current, cable=None):
    if current is None or current < 100:
        return dict(top_gap_mm=None,side_margin_mm=None,status='needs_current_rule')
    rules=json.loads(RULES_PATH.read_text(encoding='utf-8'))
    band=next(r for r in rules['user_design_policy']['top_gap_mm']
              if current>=r['min_a'] and current<r.get('max_a_exclusive',float('inf')))
    variable=band['gap_variable']
    baseline=rules['design_variables'][variable]
    if not isinstance(baseline,(int,float)) or isinstance(baseline,bool) or baseline<=0:
        raise ValueError(f'Biến khoảng nóc {variable} phải là số dương, đơn vị mm')
    cable=cable or {}
    fields=('outer_diameter_mm','minimum_inner_bend_radius_mm','lug_straight_mm','terminal_offset_mm','installation_allowance_mm')
    known=all(isinstance(cable.get(k),(int,float)) and cable[k]>=0 for k in fields) and cable.get('manufacturer_source') and cable.get('bend_angle_deg')==90
    required=sum(cable[k] for k in fields) if known else None
    # A quarter-turn envelope: internal bend radius + cable diameter + straight lug,
    # terminal offset and explicit installation allowance. Other routes need geometry.
    return dict(top_gap_mm=max(baseline,required) if known else baseline,
                side_margin_mm=rules['design_variables']['d4' if current>200 else 'd5'],status='user_rule',
                side_margin_variable='d4' if current>200 else 'd5',
                top_gap_variable=variable,top_gap_baseline_mm=baseline,
                top_gap_basis='calculated_cable_lug_envelope' if known else 'minimum_provisional_user_range',
                top_gap_reference='MCCB_body_top_to_inside_roof',
                connection_space_reference='terminal_exit_to_nearest_obstacle_along_actual_route',
                fabrication_release=False,
                required_geometry_review=['terminal_exit_direction','lug_projection','cable_route_in_side_view','door_and_handle_collision'],
                cable_space_verified=bool(known),cable_required_space_mm=required,
                missing_cable_inputs=[] if known else list(fields)+['manufacturer_source','bend_angle_deg_90'])

def check_fishbone(current):
    if current is not None and current>250:
        raise ValueError('Quy tắc thiết kế: đồng xương cá chỉ dùng khi CB chính <=250A; cần phương án phân phối khác')

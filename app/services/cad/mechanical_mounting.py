"""Keep cabinet sheet coordinates separate from verified mounting datums."""
import math


REQUIRED_DATUMS = ('rebate', 'mounting_plane', 'inner_door_plane')


def mounting_review(item):
    """No flange, support plane or usable area is inferred from a face bbox."""
    anchors = item.get('mechanical_anchors') or {}
    checked, missing = {}, []
    for role in REQUIRED_DATUMS:
        datum = anchors.get(role) or {}
        position = datum.get('depth_from_rear_mm')
        evidence = datum.get('source_handles') or []
        valid = (datum.get('verified') is True and evidence
                 and isinstance(position, (int, float)) and not isinstance(position, bool)
                 and math.isfinite(position)
                 and 0 <= position <= (item.get('dimensions') or {}).get('depth', 0))
        if valid:
            checked[role] = datum
        else:
            missing.append(role)
    return dict(status='verified_datums' if not missing else 'requires_source_datum_review',
                verified_datums=checked, missing=missing,
                coordinate_system='depth_mm_from_rear_toward_front',
                body_mount_face='mounting_plate', operating_face='inner_door',
                rebate_is_mounting_support=False,
                face_bounds_are_usable_mounting_area=False)


def check_main_device_depth(item, device):
    """Check a body mounted behind the inner door with its own handle evidence."""
    review = mounting_review(item)
    if review['missing']:
        return {**review, 'release_ready': False}
    datums = review['verified_datums']
    mount = datums['mounting_plane']['depth_from_rear_mm']
    door = datums['inner_door_plane']['depth_from_rear_mm']
    if door <= mount:
        return {**review, 'status': 'invalid_datum_order', 'release_ready': False}
    geometry = device.get('verified_mounting_geometry') or {}
    if not geometry.get('source_reference') or geometry.get('verified') is not True:
        return {**review, 'status': 'requires_device_mounting_evidence', 'release_ready': False}
    body = geometry.get('body_projection_mm')
    reach = geometry.get('operating_plane_range_mm')
    if (not isinstance(body, (int, float)) or isinstance(body, bool)
            or not math.isfinite(body) or body <= 0 or not isinstance(reach, list)
            or len(reach) != 2 or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                                    or not math.isfinite(v) for v in reach)
            or not 0 <= reach[0] <= reach[1]):
        return {**review, 'status': 'invalid_device_mounting_geometry', 'release_ready': False}
    distance = door - mount
    body_fits = body <= distance
    handle_reaches = reach[0] <= distance <= reach[1]
    return {**review, 'status': 'depth_fit' if body_fits and handle_reaches else 'depth_conflict',
            'mount_to_inner_door_mm': distance, 'body_fits': body_fits,
            'handle_reaches_inner_door': handle_reaches,
            # Depth alone does not verify holes, hinge sweep or terminal access.
            'release_ready': False, 'remaining_checks': ['mounting_holes', 'hinge_sweep',
                                                        'terminal_clearance', 'rebate_collision']}

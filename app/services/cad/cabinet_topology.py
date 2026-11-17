"""Identify physical bays and roof hardware from orthographic CAD evidence.

Repeated views are retained as references, not silently counted as extra parts.
Unconfirmed depth/partition geometry remains explicitly review-only.
"""
import math


def bounds(points):
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def area(points):
    return abs(sum(p[0]*q[1]-p[1]*q[0] for p, q in zip(points, points[1:]+points[:1])))/2


def contains(polygon, point):
    x, y = point
    inside = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def closed_loops(paths):
    """Join actual connected CAD segments, without adding closing chords.

    A lifting-eye silhouette is drawn as an arc and three separate LINEs;
    checking closed polylines alone loses the physical outside of the eye.
    """
    result, open_paths = [], []
    for points in paths:
        if len(points) < 2:
            continue
        if math.dist(points[0], points[-1]) < .03:
            if len(points) >= 4:
                result.append(points)
        else:
            open_paths.append(points)
    used = set()
    for seed in sorted(range(len(open_paths)), key=lambda i: len(open_paths[i]), reverse=True):
        if seed in used:
            continue
        chain, trial = list(open_paths[seed]), {seed}
        while math.dist(chain[0], chain[-1]) >= .03:
            adjacent = []
            for i, p in enumerate(open_paths):
                if i in used or i in trial:
                    continue
                if math.dist(chain[-1], p[0]) < .03:
                    adjacent.append((i, p))
                elif math.dist(chain[-1], p[-1]) < .03:
                    adjacent.append((i, list(reversed(p))))
            if not adjacent:
                break
            i, p = max(adjacent, key=lambda pair: len(pair[1]))
            trial.add(i)
            chain.extend(p[1:])
        if len(chain) >= 4 and math.dist(chain[0], chain[-1]) < .03 and area(chain) > .5:
            result.append(chain)
            used.update(trial)
    return result


def panel_layout(faces, width, height):
    layouts = []
    for kind in ('outer_door', 'inner_door', 'mounting_plate'):
        same = [f for f in faces if f['kind'] == kind]
        if not same:
            continue
        by_x = sorted(same, key=lambda f: f['bounds'][0])
        by_y = sorted(same, key=lambda f: f['bounds'][1])
        horizontal = (len(same) > 1 and abs(sum(f['width'] for f in same)-width) < 2
                      and all(abs(f['height']-height) < 2 for f in same)
                      and all(abs(a['bounds'][2]-b['bounds'][0]) < 2
                              and abs(a['bounds'][1]-b['bounds'][1]) < 2
                              for a, b in zip(by_x, by_x[1:])))
        vertical = (len(same) > 1 and abs(sum(f['height'] for f in same)-height) < 2
                    and all(abs(f['width']-width) < 2 for f in same)
                    and all(abs(a['bounds'][3]-b['bounds'][1]) < 2
                            and abs(a['bounds'][0]-b['bounds'][0]) < 2
                            for a, b in zip(by_y, by_y[1:])))
        if horizontal or vertical:
            offset = 0
            for n, f in enumerate(by_x if horizontal else by_y):
                layouts.append(dict(face_id=f['id'], kind=kind, physical=True, slot=n,
                    x_mm=offset if horizontal else 0, y_mm=offset if vertical else 0,
                    width_mm=f['width'], height_mm=f['height'],
                    basis='adjacent_source_bays_x' if horizontal else 'adjacent_source_bays_y'))
                offset += f['width'] if horizontal else f['height']
        else:
            # Multiple same-size full-width drawings are different projections.
            # This does not erase the source or claim internal separation.
            preferred = next((f for f in same if f.get('label', '').strip().upper() == 'EQUIPMENT VIEW'), same[0])
            same_envelope = all(abs(f['width']-width) < 2 and abs(f['height']-height) < 2 for f in same)
            for f in same:
                layouts.append(dict(face_id=f['id'], kind=kind, physical=f is preferred, slot=0,
                    x_mm=(width-f['width'])/2, y_mm=(height-f['height'])/2,
                    width_mm=f['width'], height_mm=f['height'],
                    basis='single_source_panel' if len(same) == 1 else
                          'alternate_source_projection' if same_envelope else 'source_panel_layout_unresolved'))
    return layouts


def door_perimeter_details(faces):
    """Keep inset frame outlines owned by their source outer leaf.

    FRONT alone cannot distinguish a folded return from an added stiffener,
    so neither its section nor its depth is invented here.
    """
    details = []
    for face in faces:
        if face['kind'] != 'outer_door':
            continue
        groups = {g['id']: g for g in face['groups']}
        candidates = []
        for i, p in enumerate(face['paths']):
            if not p['closed'] or groups[p['group_id']]['name']:
                continue
            b = bounds(p['points'])
            inset = [b[0], b[1], face['width']-b[2], face['height']-b[3]]
            a = area(p['points'])/(face['width']*face['height'])
            if min(inset) > .5 and max(inset) < min(face['width'], face['height'])*.2 and .5 < a < .98:
                candidates.append((i, p['group_id'], b))
        if candidates:
            details.append(dict(owner_face_id=face['id'], path_indices=[p[0] for p in candidates],
                source_handles=sorted({p[1] for p in candidates}), side='inner',
                kind='stiffener_or_fold_return', section_verified=False,
                basis='inset_perimeter_in_outer_door_source_view'))
    return details


def identify(faces, body, assembly):
    width, height, depth = body['width'], body['height'], body['depth']
    layouts = panel_layout(faces, width, height)
    lookup = {f['id']: f for f in faces}
    physical = {p['face_id']: p for p in layouts if p['physical']}
    plates = [p for p in layouts if p['physical'] and p['kind'] == 'mounting_plate']
    bay_axis = 'x' if len(plates) > 1 and all(p['basis'] == 'adjacent_source_bays_x' for p in plates) else (
        'y' if len(plates) > 1 and all(p['basis'] == 'adjacent_source_bays_y' for p in plates) else None)
    compartments = dict(count=len(plates) if bay_axis else 1, axis=bay_axis,
        slots=plates if bay_axis else [],
        basis='adjacent_source_panel_boundaries' if bay_axis else 'no_separate_bay_evidence',
        partition_depth_from_top_views=False)
    # A full-depth separator needs matching top-frame evidence, not just doors.
    top_bays = {p['bay'] for p in assembly.get('top_placements', [])}
    compartments['partition_depth_from_top_views'] = bool(bay_axis == 'x' and len(top_bays) == len(plates))

    def parts(face, role):
        return [(g, [face['paths'][i]['points'] for i in g['paths']])
                for g in face['groups'] if g['role'] == role]

    side_parts = []
    for f in faces:
        if f['kind'] in ('side', 'section') and abs(f['height']-height) < 2:
            for g, paths in parts(f, 'lifting_eye'):
                b = bounds([p for ps in paths for p in ps])
                side_parts.append(dict(face=f, group=g, paths=paths, center=(b[0]+b[2])/2))
    # Prefer SIDE over section only when it actually contains lifting hardware.
    chosen_side = next((p['face']['id'] for p in side_parts if p['face']['kind'] == 'side'), None)
    if chosen_side:
        side_parts = [p for p in side_parts if p['face']['id'] == chosen_side]

    front_slots = [p for p in layouts if p['physical'] and p['kind'] == 'outer_door']
    if not front_slots:
        front_slots = plates
    fronts = []
    for slot in front_slots:
        f = lookup[slot['face_id']]
        for g, paths in parts(f, 'lifting_eye'):
            b = bounds([p for ps in paths for p in ps])
            high = [p for ps in paths for p in ps if p[1] > f['height']+20]
            shaft = [bounds(ps) for ps in paths if len(ps) == 2 and abs(ps[0][0]-ps[1][0]) < .02
                     and abs(ps[0][1]-ps[1][1]) > 15 and max(p[1] for p in ps) <= f['height']+2]
            stem_x = [p[0] for p in shaft]
            stem_y = [p[a] for p in shaft for a in (1, 3)]
            fronts.append(dict(x=slot['x_mm']+(b[0]+b[2])/2-width/2,
                group_id=g['id'], source_face=f['id'], height=f['height'],
                thickness=max(p[0] for p in high)-min(p[0] for p in high) if high else None,
                stem_diameter=max(stem_x)-min(stem_x) if len(stem_x) > 1 else None,
                stem_range=[min(stem_y)-f['height'], max(stem_y)-f['height']] if stem_y else None))

    top_eyes = []
    side_width = next((f['width'] for f in faces if f['kind'] == 'side'), depth-20)
    for place in assembly.get('top_placements', []):
        f = lookup.get(place['face_id'])
        if not f:
            continue
        for g, paths in parts(f, 'lifting_eye'):
            b = bounds([p for ps in paths for p in ps])
            top_eyes.append(dict(x=place['x_mm']+(b[0]+b[2])/2-width/2,
                z=-depth/2+side_width-place['depth_offset_mm']-(b[1]+b[3])/2,
                group_id=g['id'], source_face=f['id']))
    # TOP provides the physical X/Z count, including four eyes whose two pairs
    # overlap in FRONT. Without TOP, one SIDE depth and FRONT X positions suffice.
    positions = top_eyes if top_eyes else [dict(x=f['x'], z=side_parts[0]['center']-depth/2,
        group_id=f['group_id'], source_face=f['source_face']) for f in fronts] if len(side_parts) == 1 else []
    eyes, issues = [], []
    if fronts and not positions:
        issues.append('lifting_eye_depth_unresolved')
    for pos in positions:
        front = min(fronts, key=lambda f: abs(f['x']-pos['x'])) if fronts else None
        side = min(side_parts, key=lambda s: abs(s['center']-depth/2-pos['z'])) if side_parts else None
        if not front or not side or abs(front['x']-pos['x']) > .2:
            issues.append('lifting_eye_projection_unresolved')
            continue
        loops = closed_loops(side['paths'])
        outer = [p for p in loops if bounds(p)[3] > height+20 and area(p) > 200]
        if not outer:
            issues.append('lifting_eye_outline_unresolved')
            continue
        silhouette = max(outer, key=area)
        holes = [p for p in loops if area(p) < area(silhouette)*.8 and bounds(p)[1] > height+5
                 and contains(silhouette, ((bounds(p)[0]+bounds(p)[2])/2, (bounds(p)[1]+bounds(p)[3])/2))]
        if not holes or not front['thickness'] or not front['stem_diameter']:
            issues.append('lifting_eye_dimensions_unresolved')
            continue
        center = side['center']
        relative = lambda ps: [[round(x-center, 3), round(y-height, 3)] for x, y in ps]
        delta = abs(side['center']-depth/2-pos['z'])
        conflict = delta > .2
        if conflict:
            issues.append('lifting_eye_projection_conflict')
        eyes.append(dict(id=f"eye-{len(eyes)+1}", x_mm=round(pos['x'], 3), z_mm=round(pos['z'], 3),
            profile=relative(silhouette), holes=[relative(max(holes, key=area))],
            thickness_mm=round(front['thickness'], 3), stem_diameter_mm=round(front['stem_diameter'], 3),
            stem_range_mm=front['stem_range'],
            source_handles=sorted({pos['group_id'], front['group_id'], side['group']['id']}),
            basis='front_top_side_projection_match' if top_eyes else 'front_side_projection_match',
            projection_conflict=conflict, projection_delta_mm=round(delta, 3)))

    lugs = []
    lug_slots = next(([p for p in layouts if p['physical'] and p['kind'] == kind
                       and parts(lookup[p['face_id']], 'mounting_lug')]
                      for kind in ('outer_door', 'mounting_plate', 'inner_door')
                      if any(p['physical'] and p['kind'] == kind
                             and parts(lookup[p['face_id']], 'mounting_lug') for p in layouts)), [])
    for slot in lug_slots:
        f = lookup[slot['face_id']]
        for g, paths in parts(f, 'mounting_lug'):
            loops = sorted(closed_loops(paths), key=area, reverse=True)
            if not loops:
                continue
            lugs.append(dict(id=g['id'], x_mm=slot['x_mm']-width/2, y_mm=slot['y_mm']-height/2,
                profile=loops[0], holes=[p for p in loops[1:] if contains(loops[0], p[0])],
                source_face=f['id'], basis='source_mounting_lug_front_contours', depth_verified=False))
    if any(not p['physical'] for p in layouts):
        issues.append('alternate_views_not_extra_bays')
    if any(p['basis'] == 'source_panel_layout_unresolved' for p in layouts):
        issues.append('source_panel_layout_unresolved')
    return dict(panel_layout=layouts, compartments=compartments, lifting_eyes=eyes,
                door_perimeter_details=door_perimeter_details(faces),
                mounting_lugs=lugs, review_issues=sorted(set(issues)))

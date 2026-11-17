"""Read-only solid-preview geometry for every indexed cabinet source.

The DXF remains authoritative. Unassigned views and nominal closing panels are
reported explicitly; this preview is not a fabrication/clearance certificate.
"""
import math
import re
import unicodedata
from functools import lru_cache

import ezdxf
from ezdxf import bbox, dynblkhelper
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Vec3
from ezdxf.path import from_hatch, make_path
from ezdxf.upright import upright

from app.services.cad import cabinet_templates as library

TOLERANCE_MM = .1


def _plain(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.upper().replace('Đ', 'D'))
                   if not unicodedata.combining(c))


def _role(name):
    name = _plain(name)
    if re.search(r'LIFTING|TAI CAU|MOC CAU|EYEBOLT|HOIST', name):
        return 'lifting_eye'
    if 'TAI TREO' in name or 'MOUNTING LUG' in name:
        return 'mounting_lug'
    if re.search(r'HL\d|HINGE|BAN LE', name):
        return 'hinge'
    if re.search(r'AB301|MS406|LOCK|KHOA|LATCH', name):
        return 'lock'
    return 'detail'


def _kind(face):
    kind, label = face['kind'], _plain(face.get('source_label', ''))
    if kind == 'front':
        return 'outer_door'
    if kind == 'inner_side' or 'E-SIDE' in label:
        return 'section'
    if kind != 'source_view_requires_boundary_review':
        return kind
    if 'BOTTOM VIEW' in label:
        return 'bottom'
    if 'TOP VIEW' in label:
        return 'top'
    return 'reference'


def _closed(points):
    return len(points) > 3 and math.dist(points[0], points[-1]) < .02


def _path_bounds(points):
    return [min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points)]


def _source_assembly(groups, faces, dimensions, body_width, body_height, specification):
    """Recover roof/base from source profiles, rather than Hnominal - Hbody.

    Some source LWPOLYLINEs have closed=False but repeat the first vertex. The
    extracted curve endpoint test, not the DXF flag, identifies their perimeter.
    """
    side = next((f for f in faces if f['kind'] == 'side'
                 and abs(f['height']-body_height) < 2), None)
    result = dict(roof=None, base=None, top_placements=[],
                  assembly_note=specification.get('ASSEMBLY', ''),
                  source_form=specification.get('FORM', ''))
    if side:
        sx, sy = side['bounds'][:2]
        profiles = []
        for group in groups:
            if group['name']:
                continue
            for points in group['paths']:
                if not _closed(points):
                    continue
                p = [[round(x-sx, 3), round(y-sy, 3)] for x, y in points]
                b = _path_bounds(p)
                if b[0] < -60 or b[2] > dimensions['depth']+60 or b[2]-b[0] < side['width']*.8:
                    continue
                profiles.append(dict(profile=p, bounds=b, source_handle=group['id']))
        roofs = [p for p in profiles if p['bounds'][1] >= body_height-100
                 and p['bounds'][3] > body_height+2 and p['bounds'][3]-p['bounds'][1] <= 180]
        if roofs:
            roof = max(roofs, key=lambda p: (p['bounds'][2]-p['bounds'][0])*(p['bounds'][3]-p['bounds'][1]))
            roof.update(width_mm=body_width, height_above_body_mm=round(roof['bounds'][3]-body_height, 3),
                        basis='source_side_roof_perimeter')
            front = next((f for f in faces if f['kind'] == 'outer_door'), None)
            if front:
                fx, fy = front['bounds'][:2]
                widths = []
                for group in groups:
                    if group['name']:
                        continue
                    for points in group['paths']:
                        if not _closed(points):
                            continue
                        b = _path_bounds(points)
                        if (abs((b[0]+b[2])/2-(fx+front['width']/2)) < 5
                            and b[1]-fy >= front['height']-100 and b[3]-fy > front['height']+2
                            and front['width']*.95 < b[2]-b[0] < front['width']+120):
                            widths.append(b[2]-b[0])
                if widths:
                    roof['width_mm'] = round(max(widths), 3)
            result['roof'] = roof
        bases = [p for p in profiles if abs(p['bounds'][3]) <= 2 and p['bounds'][1] < -5
                 and p['bounds'][3]-p['bounds'][1] <= dimensions['height']*.65]
        if bases:
            base = max(bases, key=lambda p: (p['bounds'][2]-p['bounds'][0])*(p['bounds'][3]-p['bounds'][1]))
            b = base['bounds']
            base.update(height_mm=round(b[3]-b[1], 3), depth_mm=round(b[2]-b[0], 3),
                        basis='source_side_base_perimeter', detail_groups=[])
            for group in groups:
                if not group['name'] or group['role'] != 'detail':
                    continue
                g = group['bounds']
                if g[0] >= sx+b[0]-1 and g[2] <= sx+b[2]+1 and g[1] >= sy+b[1]-1 and g[3] <= sy+b[3]+1:
                    base['detail_groups'].append(dict(name=group['name'], source_handle=group['id'],
                        paths=[dict(points=[[round(x-sx, 3), round(y-sy, 3)] for x, y in p], closed=_closed(p))
                               for p in group['paths']]))
            result['base'] = base

    # A wide cabinet can have separate removable top plates for each bay. Its
    # 891 mm plate must not be rejected because the enclosure is 1800 mm wide.
    vertical = [f for f in faces if f['kind'] in ('outer_door', 'mounting_plate')]
    plates = [f for f in faces if f['kind'] == 'mounting_plate']
    separate_bays = len(plates) > 1 and abs(sum(f['width'] for f in plates)-body_width) < 2
    seen_bays = set()
    for top in [f for f in faces if f['kind'] == 'top']:
        center = (top['bounds'][0]+top['bounds'][2])/2
        candidates = [f for f in vertical if abs((f['bounds'][0]+f['bounds'][2])/2-center) < max(100, f['width']*.15)]
        if not candidates:
            continue
        mate = min(candidates, key=lambda f: abs((f['bounds'][0]+f['bounds'][2])/2-center))
        bay = plates.index(mate) if separate_bays and mate in plates else 0
        if bay in seen_bays:
            continue
        mx = mate['bounds'][0]
        y_origins = []
        for group in groups:
            if group['name']:
                continue
            for points in group['paths']:
                if not _closed(points):
                    continue
                b = _path_bounds(points)
                if (mx-2 <= b[0] and b[2] <= mx+mate['width']+2
                    and abs((b[1]+b[3])/2-(top['bounds'][1]+top['bounds'][3])/2) < dimensions['depth']*.5
                    and dimensions['depth']*.7 <= b[3]-b[1] <= dimensions['depth']+2):
                    y_origins.append(b[1])
        origin_y = min(y_origins) if y_origins else top['bounds'][1]
        offset_x = sum(f['width'] for f in plates[:bay]) if separate_bays else (body_width-mate['width'])/2
        side_depth = next((f['width'] for f in faces if f['kind'] == 'side'), dimensions['depth'])
        # Independent drawing views may be translated a few mm on the sheet.
        # A full-width/full-depth view defines its own physical origin. Only
        # partial cover views use offsets inside their own source frame.
        x_in_bay = 0 if abs(top['width']-mate['width']) < 2 else top['bounds'][0]-mx
        depth_offset = 0 if abs(top['height']-side_depth) < 2 else top['bounds'][1]-origin_y
        result['top_placements'].append(dict(face_id=top['id'], bay=bay,
            x_mm=round(offset_x+x_in_bay, 3),
            depth_offset_mm=round(depth_offset, 3),
            bay_width_mm=mate['width'], basis='source_top_view_and_matching_vertical_bay'))
        seen_bays.add(bay)
    return result


def preview(template_id, dimensions=None):
    item = library.resolve(template_id)
    nominal = item.get('dimensions')
    if not nominal:
        raise ValueError('Form chưa có đủ kích thước để xem 3D.')
    dimensions = dimensions or nominal
    if set(dimensions) != {'width', 'height', 'depth'} or any(
            not isinstance(v, (int, float)) or not math.isfinite(v) or not 100 < v <= 10000
            for v in dimensions.values()):
        raise ValueError('Nhập đủ H × W × D trong khoảng 100–10000 mm.')
    # The cleaned source excludes title-block logos and unrelated drawing frames.
    source = (library.LIBRARY / item['filename']).resolve()
    if not source.is_relative_to(library.LIBRARY.resolve()) or not source.is_file():
        raise ValueError('Không tìm thấy CAD nguồn của form tủ.')
    catalog = library.LIBRARY / 'catalog.json'
    profiles = library.LIBRARY / 'resize_profiles.json'
    return _cached(template_id, tuple(float(dimensions[k]) for k in ('height', 'width', 'depth')),
                   source.stat().st_mtime_ns, catalog.stat().st_mtime_ns,
                   profiles.stat().st_mtime_ns if profiles.exists() else 0)


@lru_cache(maxsize=128)
def _cached(template_id, size, source_stamp, catalog_stamp, profile_stamp):
    item = library.resolve(template_id)
    source = (library.LIBRARY / item['filename']).resolve()
    doc = ezdxf.readfile(source)
    dimensions = dict(zip(('height', 'width', 'depth'), size))
    nominal = item['dimensions']
    delta = {k: dimensions[k]-nominal[k] for k in nominal}
    resizing = any(abs(v) > .01 for v in delta.values())
    profile = library.resize_profile(item)
    axes = profile['axes'] if resizing and profile else library.stretch_axes(doc, nominal) if resizing else [[], []]
    if resizing:
        supported = {b['dimension'] for bands in axes for b in bands}
        if any(not .75 <= dimensions[k]/nominal[k] <= 1.25 for k in nominal):
            raise ValueError('Kích thước vượt khoảng co giãn 75–125% của form nguồn.')
        if any(abs(delta[k]) > .01 and k not in supported for k in nominal):
            raise ValueError('Form chưa đủ mốc kích thước để co giãn theo yêu cầu.')

    def point(p):
        p = Vec3(p)
        return Vec3(library.map_coordinate(p.x, axes[0], delta),
                    library.map_coordinate(p.y, axes[1], delta), p.z)

    faces, unsupported, unassigned, warnings = [], [], 0, []
    # Avoid duplicate annotation-derived faces (e.g. "cánh trong lùi 30 mm")
    # overlapping an already indexed EQUIPMENT VIEW.
    indexed = sorted(item.get('faces', []), key=lambda f: 'VIEW' not in f.get('source_label', ''))
    for row in indexed:
        bounds = row.get('clean_bounds')
        if not bounds or any(max(abs(a-b) for a, b in zip(bounds, f['source_bounds'])) < .1 for f in faces):
            continue
        lo, hi = point((bounds[0], bounds[1], 0)), point((bounds[2], bounds[3], 0))
        faces.append(dict(id=row['id'], kind=_kind(row), label=row.get('source_label', ''),
                          source_bounds=bounds, bounds=[lo.x, lo.y, hi.x, hi.y],
                          width=hi.x-lo.x, height=hi.y-lo.y, paths=[], groups=[]))
    if not faces:
        raise ValueError('Form chưa xác định được mặt CAD để dựng 3D.')

    groups = []
    for parent in doc.modelspace():
        if parent.dxftype() in ('TEXT', 'MTEXT', 'POINT', 'DIMENSION'):
            continue
        name = ''
        if parent.dxftype() == 'INSERT':
            definition = dynblkhelper.get_dynamic_block_definition(parent)
            name = definition.name if definition else parent.dxf.name
            if name.startswith('_Open') or 'KHUNG' in _plain(name):
                continue
        role, offset = _role(name), None
        if resizing and parent.dxftype() == 'INSERT':
            bounds = bbox.extents([parent], fast=True)
            if bounds.has_data and max(bounds.size.x, bounds.size.y) < min(nominal.values())*.8:
                center = (bounds.extmin+bounds.extmax)/2
                offset = point(center)-center
                lock_offset = library.centered_lock_offset(parent, bounds, axes, delta)
                if lock_offset is not None:
                    offset = lock_offset
        paths = []
        for entity in recursive_decompose([parent]):
            if entity.dxftype() in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF', 'POINT'):
                continue
            try:
                copy = entity.copy()
                upright(copy)
                if offset is not None:
                    copy.translate(offset.x, offset.y, 0)
                elif resizing:
                    library.stretch_entity(copy, point)
                curves = from_hatch(copy) if copy.dxftype() == 'HATCH' else [make_path(copy)]
                for curve in curves:
                    for sub in curve.sub_paths():
                        points = [[round(p.x, 4), round(p.y, 4)]
                                  for p in sub.flattening(distance=TOLERANCE_MM, segments=8)]
                        if len(points) > 1:
                            paths.append(points)
            except (ezdxf.DXFError, TypeError, ValueError, AttributeError, NotImplementedError) as exc:
                unsupported.append(dict(handle=parent.dxf.handle, type=entity.dxftype(), reason=str(exc)[:160]))
        if paths:
            points = [p for path in paths for p in path]
            bounds = [min(p[0] for p in points), min(p[1] for p in points),
                      max(p[0] for p in points), max(p[1] for p in points)]
            groups.append(dict(id=parent.dxf.handle, name=name, role=role, bounds=bounds, paths=paths))

    # Additional TOP/BOTTOM/section views: only assign a boundary when a nearby
    # closed source contour matches the view's expected axes. No stretched image.
    for row in indexed:
        kind = _kind(row)
        if row.get('clean_bounds') or kind not in ('top', 'bottom', 'section'):
            continue
        label = row.get('label_position_clean')
        if not label:
            continue
        label = point((*label[:2], 0))
        want_w, want_h = ((dimensions['depth'], dimensions['height']) if kind == 'section'
                          else (dimensions['width'], dimensions['depth']))
        # An indexed horizontal face may be a removable plate for one bay,
        # not the full enclosure width. Recover its sibling by the same source
        # dimensions instead of rejecting it against nominal W (e.g. 1800 mm).
        same_kind = next((f for f in faces if f['kind'] == kind), None)
        if kind in ('top', 'bottom') and same_kind and same_kind['width'] < dimensions['width']*.75:
            want_w, want_h = same_kind['width'], same_kind['height']
        candidates = []
        for group in groups:
            if group['name']:
                continue
            for points in group['paths']:
                if not _closed(points):
                    continue
                b = [min(p[0] for p in points), min(p[1] for p in points),
                     max(p[0] for p in points), max(p[1] for p in points)]
                w, h = b[2]-b[0], b[3]-b[1]
                if abs(w-want_w) > max(35, want_w*.06) or abs(h-want_h) > max(35, want_h*.06):
                    continue
                if abs((b[0]+b[2])/2-label.x) > max(70, want_w*.15):
                    continue
                distance = min(abs(b[1]-label.y), abs(b[3]-label.y))
                if distance <= 350:
                    candidates.append((distance+abs(w-want_w)+abs(h-want_h), b))
        basis = 'source_closed_perimeter'
        if not candidates:
            # Some multi-bay top views are a pair of separate folded side
            # profiles, not one outer closed polyline. Bound their actual
            # matching frame pieces; never clone the neighbouring cover.
            bays = [f for f in faces if f['kind'] == 'mounting_plate']
            mate = min(bays, key=lambda f: abs((f['bounds'][0]+f['bounds'][2])/2-label.x)) if bays else None
            frame_pieces = []
            if (kind in ('top', 'bottom') and mate and len(bays) > 1
                and abs(sum(f['width'] for f in bays)-dimensions['width']) < 2
                and abs((mate['bounds'][0]+mate['bounds'][2])/2-label.x) < mate['width']*.2):
                for group in groups:
                    if group['name']:
                        continue
                    for points in group['paths']:
                        if not _closed(points):
                            continue
                        pb = _path_bounds(points)
                        if (mate['bounds'][0]-2 <= pb[0] and pb[2] <= mate['bounds'][2]+2
                            and label.y+15 <= pb[1] and pb[3] <= label.y+dimensions['depth']+350
                            and dimensions['depth']*.7 <= pb[3]-pb[1] <= dimensions['depth']+2):
                            frame_pieces.append(pb)
            if not frame_pieces:
                continue
            b = [min(p[0] for p in frame_pieces), min(p[1] for p in frame_pieces),
                 max(p[2] for p in frame_pieces), max(p[3] for p in frame_pieces)]
            if abs(b[2]-b[0]-mate['width']) > 2:
                continue
            basis = 'source_top_frame_envelope'
        else:
            b = min(candidates, key=lambda c: c[0])[1]
        if any(max(abs(a-c) for a, c in zip(b, f['bounds'])) < 2 for f in faces):
            continue
        faces.append(dict(id=row['id'], kind=kind, label=row.get('source_label', ''),
                          source_bounds=None, bounds=b, width=b[2]-b[0], height=b[3]-b[1],
                          identification_basis=basis, paths=[], groups=[]))

    for group in groups:
        b = group['bounds']
        cx, cy = (b[0]+b[2])/2, (b[1]+b[3])/2
        candidates = []
        for face in faces:
            f = face['bounds']
            dx, dy = max(f[0]-cx, 0, cx-f[2]), max(f[1]-cy, 0, cy-f[3])
            margin = 60 if group['role'] == 'mounting_lug' else 35
            if dx <= margin and dy <= margin:
                candidates.append((dx+dy, face))
        if not candidates:
            unassigned += len(group['paths'])
            continue
        face = min(candidates, key=lambda p: p[0])[1]
        x, y = face['bounds'][:2]
        # Prevent distant annotation/dimension lines crossing the view from
        # becoming extruded "hardware". Source CAD is always available intact.
        if group['role'] == 'detail' and not group['name'] and (
                b[2]-b[0] > face['width']+100 or b[3]-b[1] > face['height']+100):
            unassigned += len(group['paths'])
            continue
        group_paths = []
        for points in group['paths']:
            local = [[round(p[0]-x, 3), round(p[1]-y, 3)] for p in points]
            row = dict(points=local, closed=_closed(local), group_id=group['id'])
            face['paths'].append(row)
            group_paths.append(len(face['paths'])-1)
        face['groups'].append(dict(id=group['id'], name=group['name'], role=group['role'], paths=group_paths))

    # Prefer explicitly labeled door outlines, not an annotation-derived plane.
    front = next((f for f in faces if f['kind'] == 'outer_door'), None)
    vertical = front or next((f for f in faces if f['kind'] == 'mounting_plate'), faces[0])
    body_w, body_h = vertical['width'], vertical['height']
    if not front:
        body_w = dimensions['width']
        warnings.append('front_outline_missing')
    assembly = _source_assembly(groups, faces, dimensions, body_w, body_h, item.get('source_specification', {}))
    from app.services.cad.cabinet_topology import identify
    assembly.update(identify(faces, dict(width=body_w, height=body_h, depth=dimensions['depth']), assembly))
    warnings.extend(assembly['review_issues'])
    if abs(body_w-dimensions['width']) > 2 or abs(body_h-dimensions['height']) > 2:
        warnings.append('source_body_differs_from_nominal')
    for kind in ('top', 'bottom'):
        same = [f for f in faces if f['kind'] == kind]
        matched_top_bays = (kind == 'top' and assembly['compartments']['count'] > 1
                            and len(assembly['top_placements']) == assembly['compartments']['count'])
        if len(same) > 1 and not matched_top_bays:
            warnings.append(f'multiple_{kind}_views')
    if unsupported:
        warnings.append('unsupported_source_entities')
    warnings.extend(['nominal_closing_panels', 'hardware_depth_provisional', 'interior_offsets_provisional'])
    # Multiple plates may describe separate bays, not extra copies on one plane.
    for kind in ('outer_door', 'inner_door', 'mounting_plate'):
        same = [f for f in faces if f['kind'] == kind]
        for n, face in enumerate(same):
            face['bay'] = n
            face['bay_count'] = len(same)
    thickness = item.get('sheet_thickness_mm')
    return dict(schema_version=3, template_id=template_id, dimensions=dimensions, assembly=assembly,
                body_dimensions=dict(width=body_w, height=body_h, depth=dimensions['depth']),
                sheet_thickness_mm=thickness or 1.5, thickness_from_source=bool(thickness),
                source_file=item['filename'], faces=faces, warnings=warnings,
                description=item.get('description', ''), curve_tolerance_mm=TOLERANCE_MM,
                coverage=dict(paths=sum(len(f['paths']) for f in faces),
                              unassigned_paths=unassigned, unsupported=unsupported),
                status='source_based_preview_requires_mechanical_review')

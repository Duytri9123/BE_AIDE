"""Audit every source profile and qualify existing shared CAD without guessing sizes.

Run after export_device_blocks.py. Original DXF and profile files are read only.
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.cad.catalogtb_assets import face_code, insertion_source
from app.services.cad.device_installation import installation_review
from app.services.customer_equipment_information import public_view_id


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def conductor_aperture(paths):
    """Join source segments on an explicitly labelled wire-passage projection.

    The largest internal loop is the conductor window, never a door cutout.
    Ambiguous/missing closed loops are left unmodelled.
    """
    near = lambda a, b: math.dist(a, b) < .002
    pending = [list(line) for line in paths if len(line) >= 2]
    loops = []
    while pending:
        line = pending.pop(0)
        while not near(line[0], line[-1]):
            found = False
            for i, other in enumerate(pending):
                if near(line[-1], other[0]):
                    line.extend(other[1:])
                elif near(line[-1], other[-1]):
                    line.extend(list(reversed(other))[1:])
                else:
                    continue
                pending.pop(i)
                found = True
                break
            if not found:
                break
        if len(line) >= 4 and near(line[0], line[-1]):
            loops.append(line)
    area = lambda p: abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(p,p[1:]))) / 2
    loops.sort(key=area, reverse=True)
    if len(loops) < 2:
        return []
    outer = loops[0]
    def inside(point):
        crossings = 0
        for a,b in zip(outer,outer[1:]):
            if (a[1] > point[1]) != (b[1] > point[1]) and point[0] < (b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0]:
                crossings += 1
        return crossings % 2 == 1
    internal = [loop for loop in loops[1:] if area(loop) > 4 and all(inside(p) for p in loop[:-1])]
    return internal[:1]


def review(root, exported, mechanical_models=()):
    profiles_path = exported / 'cad-profiles.json'
    published = json.loads(profiles_path.read_text(encoding='utf8'))
    by_id = {p['id']: p for p in published}
    rows = []
    for path in sorted(root.rglob('thong_tin_thiet_bi.json')):
        source = json.loads(path.read_text(encoding='utf-8-sig'))
        relative = path.relative_to(root).as_posix()
        profile_id = 'TB-' + hashlib.sha1(relative.encode()).hexdigest()[:16]
        exported_profile = by_id.get(profile_id)
        indexed = {v['view_id']: v for v in (exported_profile or {}).get('views', [])}
        groups = defaultdict(list)
        for view in source.get('cad_don') or []:
            # Public view IDs hash the original entry identifier, as the API does.
            geometry = indexed.get(public_view_id(view['id_hinh_goc']))
            if geometry is None:
                continue
            variant = str(view.get('bien_the_cad') or view.get('bien_the') or '')
            geometry['variant_id'] = variant
            geometry['face'] = face_code(view.get('huong_nhin'))
            geometry['model_codes'] = view.get('model_codes') or []
            evidence = view.get('unit_verification') or {}
            geometry['dimension_source'] = evidence.get('source_url')
            try:
                original = (path.parent / view['duong_dan']).resolve()
                if not original.is_relative_to(root.resolve()):
                    raise ValueError('Source outside catalog')
                actual = insertion_source(original)
                geometry['source_matches'] = hashlib.sha256(actual.read_bytes()).hexdigest() == geometry.get('sha256')
            except (KeyError, OSError, ValueError):
                geometry['source_matches'] = False
            groups[variant].append(geometry)
        assemblies = []
        for variant, views in groups.items():
            fronts = [v for v in views if v['face'] in {'front', 'wire_passage'} and v.get('geometry_ref') and v.get('source_matches')]
            sides = [v for v in views if v['face'] == 'side' and v.get('geometry_ref') and v.get('source_matches')]
            issues = []
            if any(not v.get('source_matches') for v in views):
                issues.append('source_missing_or_changed')
            if len(fronts) != 1:
                issues.append('front_missing_or_ambiguous')
            if len(sides) != 1:
                issues.append('side_missing_or_ambiguous')
            dimensions = None
            if not issues:
                front, side = fronts[0], sides[0]
                if not all(positive(v) for v in [front.get('width'), front.get('height'), side.get('width'), side.get('height')]):
                    issues.append('invalid_dimensions')
                elif abs(front['height'] - side['height']) > max(2, front['height'] * .05):
                    issues.append('projection_height_mismatch')
                else:
                    dimensions = dict(width=front['width'], height=front['height'], depth=side['width'])
            installation = installation_review(source, path, variant_id=variant)
            assemblies.append(dict(variant_id=variant, can_build_source_solid=not issues,
                dimensions_mm=dimensions, issues=issues, dimensions_verified=False,
                geometry_status='source_silhouette_envelope' if not issues else 'source_projection_only',
                auto_cutout_allowed=installation['auto_cutout_allowed']))
            if not issues:
                if fronts[0]['face'] == 'wire_passage':
                    geometry_path = exported / fronts[0]['geometry_ref']
                    if not geometry_path.resolve().is_relative_to(exported.resolve()):
                        raise ValueError('Geometry outside export directory')
                    with gzip.open(geometry_path, 'rt', encoding='utf8') as stream:
                        holes = conductor_aperture(json.load(stream)['paths'])
                    if holes:
                        assemblies[-1]['through_holes_mm'] = holes
                        assemblies[-1]['through_holes_basis'] = 'closed_conductor_window_in_wire_passage_CAD'
                for model in mechanical_models:
                    if (model.get('mechanics') and model.get('front', {}).get('sha256') and
                            model['front']['sha256'] == fronts[0].get('sha256') and
                            model.get('side', {}).get('sha256') == sides[0].get('sha256')):
                        assemblies[-1]['mechanics'] = model['mechanics']
                        assemblies[-1]['mechanics_basis'] = 'matching_source_front_and_side_sha256'
        if exported_profile is not None:
            exported_profile['assemblies'] = assemblies
            exported_profile['dimensions_verified'] = False
            installation = installation_review(source, path)
            exported_profile['installation_review'] = {k: installation[k] for k in
                ('category', 'body_ownership', 'body_on_door_allowed', 'operator_is_separate_from_body',
                 'auto_cutout_allowed', 'front_bbox_is_cutout', 'release_ready')}
        rows.append(dict(profile=relative, id=profile_id,
            name=source.get('ten_san_pham') or source.get('ten_kieu') or path.parent.name,
            source_profile_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            source_views=len(source.get('cad_don') or []), exported=exported_profile is not None,
            assemblies=assemblies, installation=installation_review(source, path)))
    counts = Counter(issue for r in rows for a in r['assemblies'] for issue in a['issues'])
    summary = dict(source_profiles=len(rows), exported_profiles=len(published),
        source_views=sum(r['source_views'] for r in rows),
        source_solid_variants=sum(a['can_build_source_solid'] for r in rows for a in r['assemblies']),
        profiles_without_export=sum(not r['exported'] for r in rows),
        verified_cutout_profiles=sum(r['installation']['auto_cutout_allowed'] for r in rows),
        issue_counts=dict(counts), manufacturer_dimensions_verified=0,
        original_profiles_modified=0, original_dxf_modified=0)
    profiles_path.write_text(json.dumps(published, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
    return dict(summary=summary, items=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, default=Path(__file__).resolve().parents[1] / 'data/CatalogTB')
    parser.add_argument('--exported', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--mechanical-library', type=Path)
    args = parser.parse_args()
    models = json.loads(args.mechanical_library.read_text(encoding='utf8'))['devices'] if args.mechanical_library else []
    result = review(args.catalog, args.exported, models)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(result['summary']))

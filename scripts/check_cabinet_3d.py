"""Validate source geometry coverage and resized previews across the library.

Run from BE_AIDE: python scripts/check_cabinet_3d.py --output ../reports/cabinet-3d
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.cad import cabinet_templates as library
from app.services.cad.cabinet_preview_3d import preview


def check(model):
    assert model['faces'], 'No indexed faces'
    assert all(math.isfinite(v) and v > 100 for v in model['body_dimensions'].values())
    assert 0 < model['sheet_thickness_mm'] < 10
    assert model['coverage']['paths'] > 0
    assembly = model.get('assembly', {})
    if assembly.get('base'):
        base = assembly['base']
        ys = [p[1] for p in base['profile']]
        assert abs(max(ys)-min(ys)-base['height_mm']) < .01
        assert base['basis'] == 'source_side_base_perimeter'
    if assembly.get('roof'):
        roof = assembly['roof']
        assert abs(max(p[1] for p in roof['profile'])-model['body_dimensions']['height']-roof['height_above_body_mm']) < .01
        assert roof['basis'] == 'source_side_roof_perimeter'
    layout = assembly.get('panel_layout', [])
    body = model['body_dimensions']
    for p in layout:
        if p['physical']:
            assert p['x_mm'] >= -2 and p['x_mm']+p['width_mm'] <= body['width']+2
            assert p['y_mm'] >= -2 and p['y_mm']+p['height_mm'] <= body['height']+2
    eyes = assembly.get('lifting_eyes', [])
    assert len({(e['x_mm'], e['z_mm']) for e in eyes}) == len(eyes), 'Duplicated physical eye'
    for eye in eyes:
        assert eye['holes'] and eye['thickness_mm'] > 0 and eye['stem_diameter_mm'] > 0
        assert all(math.isfinite(v) for p in eye['profile'] for v in p)
        assert abs(eye['x_mm']) < body['width']/2 + 2
        assert abs(eye['z_mm']) < body['depth']/2 + 2
    for face in model['faces']:
        assert face['width'] > 0 and face['height'] > 0
        assert len({g['id'] for g in face['groups']}) == len(face['groups'])
        assert all(math.isfinite(v) for p in face['paths'] for point in p['points'] for v in point)
        for group in face['groups']:
            assert all(0 <= i < len(face['paths']) for i in group['paths'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-only', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows, failures, resized = [], [], 0
    library_rows = library.inventory()
    for n, item in enumerate(library_rows):
        try:
            model = preview(item['id'])
            check(model)
            # Native CAD block hardware must never be replaced by other templates.
            assert model['template_id'] == item['id']
            assert model['source_file'] == item['filename']
            profile = library.resize_profile(item)
            if profile and not args.native_only:
                dimensions = dict(item['dimensions'])
                dimension = profile['supported'][0]
                dimensions[dimension] *= 1.1
                scaled = preview(item['id'], dimensions)
                check(scaled)
                assert scaled['dimensions'] == dimensions
                # A named hardware block moves rigidly; it must not grow with the enclosure.
                before = {g['name']: [f['paths'][i]['points'] for i in g['paths']]
                          for f in model['faces'] for g in f['groups'] if g['role'] in ('lock', 'hinge')}
                after = {g['name']: [f['paths'][i]['points'] for i in g['paths']]
                         for f in scaled['faces'] for g in f['groups'] if g['role'] in ('lock', 'hinge')}
                for name in before.keys() & after.keys():
                    for a, b in zip(before[name], after[name]):
                        if len(a) == len(b):
                            for axis in (0, 1):
                                da = max(p[axis] for p in a)-min(p[axis] for p in a)
                                db = max(p[axis] for p in b)-min(p[axis] for p in b)
                                assert abs(da-db) < .01, (item['id'], name, da, db)
                resized += 1
            path = args.output / (item['id'] + '.json')
            path.write_text(json.dumps(model, ensure_ascii=False, separators=(',', ':')), encoding='utf8')
            rows.append(dict(id=item['id'], faces=len(model['faces']), coverage=model['coverage'],
                             warnings=model['warnings'], bytes=path.stat().st_size))
        except Exception as exc:
            failures.append(dict(id=item['id'], error=repr(exc)))
        if n % 15 == 0:
            print(f'{n+1}/{len(library_rows)} checked', flush=True)
    # Reject partial sizes and unavailable templates, never return another cabinet.
    for template_id, dimensions in [(library_rows[0]['id'], {'height': 700}), ('not-a-template', None),
                                     (library_rows[0]['id'], dict(height=float('nan'), width=500, depth=250))]:
        try:
            preview(template_id, dimensions)
            failures.append(dict(id=template_id, error='Invalid input was accepted'))
        except ValueError:
            pass
    report = dict(total=len(library_rows), passed=len(rows), resized=resized, failures=failures, models=rows)
    (args.output/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(dict(total=report['total'], passed=len(rows), resized=resized, failures=failures), ensure_ascii=True), flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())

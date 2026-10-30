"""Publish inspected GMP mechanical references without unsupported price links."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_ls_wide_native_supplements import source_entities
from ls_native_writer import CAT, ROOT, write_profile
import ezdxf

OUT = ROOT / 'docs/ls-all-cad-2026-10-24'
JOBS = [
    ('GMP22-3P', 'b6e905b2712b79d2', ['GMP22-3P', 'GMP22-3PR'], 0),
    ('GMP40-P', '8850b23a90cefe6d', ['GMP40-2P', 'GMP40-3P', 'GMP40-3PR'], -6.010150394),
]


def main(refresh=True):
    additions = []
    for family, key, models, shift in JOBS:
        folder = CAT / 'LS/NguonBenNgoai' / ('RU-' + key)
        doc = ezdxf.readfile(folder / 'source.dxf')
        assert doc.units == 4 and not doc.audit().errors
        windows = [('FRONT', 'Mặt trước', (130, 190, 205, 283)),
                   ('SIDE', 'Mặt bên', (255, 190, 345, 283)),
                   ('REAR', 'Mặt sau', (375, 190, 432, 283))]
        windows = [(code, label, tuple(n + shift for n in bounds))
                   for code, label, bounds in windows]
        evidence = json.loads((folder / 'source.json').read_text(encoding='utf8'))
        evidence.update(
            review_status='mechanical_model_reference_only',
            source_dxf_sha256=hashlib.sha256((folder / 'source.dxf').read_bytes()).hexdigest(),
            reviewed_models=models, native_style_preserved=True,
            unit_evidence='INSUNITS=4; title block mm; dimensioned 44 mm rear and 87.5 mm side',
            reviewed_windows=[{'face': code, 'window': bounds} for code, _, bounds in windows],
            six_views_verified=False,
            price_link_gap='Queued 1a1b contact configuration is not established by this mechanical sheet; no price options approved.',
        )
        profile = write_profile(
            'RU-' + family, 'LS · Rơ le bảo vệ động cơ · ' + ' / '.join(models),
            'RELAY', models, None, [],
            [(code, label, [e for e in source_entities(doc, bounds) if e.dxf.layer != 'DI'])
             for code, label, bounds in windows],
            evidence, native_document=doc,
        )
        additions.append({'family': family, 'profile': profile.relative_to(CAT).as_posix(),
                          'views': 3, 'price_links_added': 0, 'evidence': evidence})
    (OUT / 'continuation-source-review.json').write_text(
        json.dumps({'date': '2026-10-25', 'additions': additions,
                    'rejected_source': {'path': 'LS/NguonBenNgoai/RU-0039d43c4bc97078/source.dxf',
                                        'reason': 'INSUNITS=0; multiple dimension overrides disagree with geometry (e.g. 100 drawn / 200 labelled). No uniform mm scale established; MT-150/225/400/800 remain gaps.'}},
                   ensure_ascii=False, indent=2), encoding='utf8')
    if not refresh:
        return additions
    if (OUT / 'gmp-price-links-20261025.json').exists():
        from link_ls_gmp_reviewed_20261025 import main as link_reviewed
        link_reviewed()
    # Refresh the file-backed browser cache; no configuration links are inferred.
    from app.services.catalogtb_browser import _refresh_browser_data
    _refresh_browser_data(CAT)
    import audit_ls_pricebook_cad_coverage as audit
    audit.OUT = OUT
    result = audit.main()
    reconcile(result)
    return result


def reconcile(result):
    """Keep the continuation's public summaries and explicit gaps consistent."""
    s = result['summary']
    summary = dict(total=s['total_price_rows'], linked=s['linked_price_rows'],
                   missing=s['missing_price_rows'], six_views=s['six_view_price_rows'],
                   partial=s['incomplete_view_price_rows'], public_profiles=s['visible_ls_profiles'],
                   public_faces=s['visible_ls_views'],
                   method='Exact public row-detail API linkage including poles, coil, contacts, selected model and same CAD variant')
    items = []
    for row in result['rows']:
        families = [dict(catalog_id=p['catalog_id'], variant_id=v['variant'],
                         faces=len(p['views']), **{k: val for k, val in v.items() if k != 'variant'})
                    for p in row['profiles'] for v in p['view_sets']]
        complete = any(f['complete'] for f in families)
        items.append(dict(id=row['price_row_id'], sku=row['sku'], category=row['category'],
                          linked=bool(families), six_views=complete, cad_families=families))
    gaps = []
    for item in items:
        if item['six_views']:
            continue
        best = min(item['cad_families'], key=lambda f: len(f['missing_faces']), default=None)
        reason = ('Source-backed CAD is partial; six orthographic views of one configuration are still required.'
                  if best else 'No reviewed CAD source establishes this model and configuration.')
        if item['sku'].startswith(('GMP22', 'GMP40')):
            reason += ' See gmp-price-links-20261025.json for independently reviewed 1a1b model links; missing views remain unresolved and source sets must not be merged.'
        gaps.append(dict(**item, status='missing_faces' if best else 'missing_verified_pricebook_cad',
                         missing_faces=best['missing_faces'] if best else ['front', 'rear', 'left', 'right', 'top', 'bottom'],
                         gap_reason=reason))
    for name, value in [('strict-public-price-coverage.json', dict(summary=summary, items=items)),
                        ('cad-supplement-queue.json', dict(summary=summary, items=gaps))]:
        (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
    from app.services.catalogtb_browser import browser_data
    from app.services.catalog_publication_policy import public_device_allowed
    from app.services.cad.ls_view_coverage import is_ls
    devices = [d for d in browser_data()['items'] if is_ls(d.get('brand')) and public_device_allowed(d)]
    counts = Counter(len(d['views']) for d in devices)
    inventory = dict(profiles=len(devices), views=sum(len(d['views']) for d in devices),
                     single_view_profiles=[d['id'] for d in devices if len(d['views']) == 1],
                     min_views=min(counts), by_face_count=dict(sorted(counts.items())))
    (OUT / 'current-public-inventory.json').write_text(json.dumps(inventory, indent=2), encoding='utf8')
    validation = []
    for profile in (CAT / 'LS/ThietBi').glob('OFFICIAL-RU-GMP*/thong_tin_thiet_bi.json'):
        p = json.loads(profile.read_text(encoding='utf8'))
        assert all(o.get('configuration_evidence') for o in p['catalog_tham_khao']['options'])
        for view in p['cad_don']:
            path = profile.parent / view['duong_dan']
            d = ezdxf.readfile(path)
            a = d.audit()
            assert d.units == 4 and not a.errors and not a.fixes
            assert all(e.dxf.layer != 'DI' for e in d.modelspace())
            validation.append(dict(path=path.relative_to(CAT).as_posix(), units=d.units,
                                   entities=len(d.modelspace()), audit_errors=0, audit_fixes=0,
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT / 'continuation-validation.json').write_text(json.dumps(validation, indent=2), encoding='utf8')
    assert len(gaps) == summary['missing'] + summary['partial']


if __name__ == '__main__':
    main()

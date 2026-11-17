"""Inspect every current profile, independent of stale index snapshots; no source edits."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.cad.device_installation import installation_review


def audit(root):
    rows = []
    for path in sorted(root.rglob('thong_tin_thiet_bi.json')):
        profile = json.loads(path.read_text(encoding='utf-8-sig'))
        review = installation_review(profile, path)
        views = profile.get('cad_don') or []
        rows.append(dict(profile=path.relative_to(root).as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            name=profile.get('ten_san_pham') or profile.get('ten_kieu') or path.parent.name,
            view_count=len(views), hidden=bool(profile.get('browser_hidden')),
            possible_cutout_views=[v['id_hinh_goc'] for v in views if
                v.get('vai_tro_cad') == 'door_cutout' or 'khoét' in str(v.get('huong_nhin','')).lower()],
            **review))
    summary = dict(profiles=len(rows), views=sum(r['view_count'] for r in rows),
        body_ownership=dict(Counter(r['body_ownership'] for r in rows)),
        verified_cutouts=sum(r['auto_cutout_allowed'] for r in rows),
        profiles_with_possible_cutout_view=sum(bool(r['possible_cutout_views']) for r in rows),
        missing_cutout_evidence=sum(not r['auto_cutout_allowed'] for r in rows),
        source_profiles_modified=0, release_ready=False)
    return dict(summary=summary, items=rows)


if __name__ == '__main__':
    backend = Path(__file__).resolve().parents[1]
    result = audit(backend / 'data/CatalogTB')
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else backend.parent / 'reports/cabinet-3d-20261115/local-ui/installation-review.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False), encoding='utf8')
    print(json.dumps(result['summary']))

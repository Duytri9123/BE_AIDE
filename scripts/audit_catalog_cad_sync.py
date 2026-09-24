"""Report exact SKU references separately from candidates needing confirmation."""
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.api.v1.endpoints.cad_library import manifest
from app.services.cad.library_taxonomy import normalize


def audit():
    catalog = json.loads((ROOT / 'data/catalog_data.json').read_text(encoding='utf8'))
    assets = manifest()['items']
    exact, candidates, unmatched = [], [], []
    for model in catalog:
        code = str(model.get('manufacturer_sku') or model['ma']).strip()
        matches = [a for a in assets if normalize(a['source_block']).strip() == normalize(code)]
        if matches:
            exact.append({'sku': model['ma'], 'assets': [a['id'] for a in matches], 'basis': 'exact_source_block_name',
                          'geometry_verified': False})
            continue
        series = str(model.get('series') or '')
        options = [a for a in assets if len(series) >= 4 and re.search(r'(?<![a-z0-9])' + re.escape(normalize(series)) + r'(?![a-z0-9])', normalize(a['source_block']))]
        if options:
            candidates.append({'sku': model['ma'], 'series': series, 'assets': [a['id'] for a in options],
                               'reason': 'Trùng series; cần xác nhận số cực, khung và kích thước trước khi gắn CAD'})
        else: unmatched.append(model['ma'])
    report = {'catalog_count': len(catalog), 'cad_asset_count': len(assets), 'exact_name_matches': exact,
              'series_candidates': candidates, 'unmatched_skus': unmatched}
    (ROOT / 'data/catalog_cad_sync_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print({k: len(v) if isinstance(v, list) else v for k, v in report.items()})


if __name__ == '__main__': audit()

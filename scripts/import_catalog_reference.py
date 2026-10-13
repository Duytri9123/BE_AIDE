"""Stage supplied technical references without publishing prices or library assets."""
import hashlib
import json
import sys
from pathlib import Path


def import_reference(source, target):
    raw = Path(source).read_bytes()
    rows = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(rows, list) or any(not isinstance(row, dict) or not row.get('ma') for row in rows):
        raise ValueError('Expected equipment rows with a model identifier')
    checksum = hashlib.sha256(raw).hexdigest()
    staged = []
    for index, row in enumerate(rows):
        staged.append({
            'reference_id': f'reference:{checksum[:16]}:{index}',
            'brand': row.get('brand'), 'brand_display': row.get('brand_display'),
            'item_name': row['ma'], 'name': row.get('n'), 'category': row.get('t'),
            'series': row.get('series'),
            'technical_data': {key: value for key, value in row.items()
                               if key not in {'g', 'brand', 'brand_display', 'ma', 'n', 't', 'series'}},
            'review_status': 'pending', 'equipment_catalog_id': None,
            # A source flag without manufacturer evidence does not approve dimensions.
            'drawing_ready': False,
        })
    payload = {'schema_version': 1, 'source_filename': Path(source).name,
               'source_sha256': checksum, 'review_status': 'pending',
               'prices_published': False, 'library_imported': False, 'items': staged}
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix('.json.tmp')
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    pending.replace(path)
    return payload


if __name__ == '__main__':
    target = Path(__file__).resolve().parents[1] / 'app/data/catalog_reference_candidates.json'
    result = import_reference(sys.argv[1], target)
    print(json.dumps({'staged_rows': len(result['items']), 'library_imported': False,
                      'prices_published': False}))

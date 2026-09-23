"""Use table headings and placed-block provenance instead of guessing opaque names."""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.cad.library_taxonomy import classify


def enrich():
    root = ROOT / 'data/device_layouts'
    cells_path = root / 'source_cells/manifest.json'
    parts_path = root / 'source_components/manifest.json'
    cells = json.loads(cells_path.read_text(encoding='utf8'))
    parts = json.loads(parts_path.read_text(encoding='utf8'))
    bounds = json.loads((ROOT / 'tmp/multibrand/cells.json').read_text())
    texts = json.loads((ROOT / 'tmp/multibrand/combined.spatial.json').read_text(encoding='utf8'))['texts']
    by_handle = {c[0]: c for c in bounds}
    parents = {i['id']: i for i in cells['items']}
    for cell in cells['items']:
        box = by_handle.get(cell['source_block'].replace('Ô ', ''))
        if not box:
            continue
        outer = next((c for c in bounds if 2600 < c[4] - c[2] < 3000 and
                      c[1] <= box[1] and c[2] <= box[2] and c[3] >= box[3] and c[4] >= box[4]), None)
        if not outer:
            continue
        headings = [t['text'].strip() for t in texts if outer[1] < t['x'] < outer[3] and outer[4]-100 < t['y'] < outer[4]]
        section = ' / '.join(headings)
        if classify(section)['kind'] != 'unclassified':
            cell['section'] = section
            # Specific row labels take precedence over the broad table heading.
            cell['category'] = cell['name'] if classify(cell['name'])['kind'] != 'unclassified' else section
    block_categories = defaultdict(set)
    for part in parts['items']:
        parent = parents.get(part['parent_asset_id'])
        if parent:
            part['section'] = parent.get('section', '')
            part['category'] = parent['category']
        if classify(part['name'], part['category'])['kind'] != 'unclassified':
            block_categories[part['source_block']].add(part['category'])
    combined_path = root / 'combined/manifest.json'
    combined = json.loads(combined_path.read_text(encoding='utf8'))
    for item in combined['items']:
        categories = block_categories.get(item['source_block'], set())
        if len(categories) == 1:
            item['category'] = next(iter(categories))
            item['classification_basis'] = 'source_table_and_placed_block'
    for path, data in [(cells_path, cells), (parts_path, parts), (combined_path, combined)]:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    enrich()

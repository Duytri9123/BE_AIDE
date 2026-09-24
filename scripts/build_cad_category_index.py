"""Create small browsable category manifests without moving source DXFs."""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.cad.library_taxonomy import classify


def slug(value):
    normalized = unicodedata.normalize('NFD', value.lower().replace('đ', 'd'))
    return re.sub(r'[^a-z0-9]+', '-', ''.join(c for c in normalized if not unicodedata.combining(c))).strip('-') or 'other'


def build():
    destination = ROOT / 'data/cad_categories'
    grouped = defaultdict(list)
    for manifest in sorted((ROOT / 'data/device_layouts').glob('*/manifest.json')):
        library = manifest.parent.name
        for item in json.loads(manifest.read_text(encoding='utf8'))['items']:
            source = Path('data/device_layouts') / library / item['filename']
            if not (ROOT / source).is_file():
                continue
            category = classify(item['name'], item.get('category', ''))
            grouped[(category['kind'], category['group'], library)].append({
                'id': item['id'], 'name': item['name'], 'source': source.as_posix(),
                'source_file': item.get('source_file', ''),
            })
    categories = defaultdict(int)
    for (kind, group, library), assets in sorted(grouped.items()):
        folder = destination / slug(kind) / slug(group)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{library}.json').write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding='utf8')
        categories[(kind, group)] += len(assets)
    index = [dict(kind=kind, group=group, count=count,
                  folder=f'{slug(kind)}/{slug(group)}')
             for (kind, group), count in sorted(categories.items())]
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf8')
    return index


if __name__ == '__main__':
    print(f'{len(build())} CAD categories indexed')

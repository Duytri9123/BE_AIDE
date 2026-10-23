"""Recheck published measurement hashes/annotation exclusions and public output."""
import collections, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.measure_customer_cad_views import CACHE, CAT, KEY, ROOT, has_annotation_entities
from app.services.customer_equipment_information import customer_device
from app.services.customer_technical_specs import _load

def main():
    cache = json.loads(CACHE.read_text(encoding='utf8'))
    removed = {}
    for vid, row in list(cache['views'].items()):
        data = (CAT / row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256'] or has_annotation_entities(data):
            removed[vid] = 'changed source or annotation entities'
            del cache['views'][vid]
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf8')
    path = ROOT / 'app/data/catalog_customer_technical_facts.json'
    registry = json.loads(path.read_text(encoding='utf8'))
    for cid, row in registry['items'].items():
        for vid, facts in row.get('view_facts', {}).items():
            if f'{cid}:{vid}' not in cache['views']:
                facts.pop(KEY, None)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf8')
    _load.cache_clear()
    snapshot = json.loads((CAT / '_agent_index/browser_display_v5.json').read_text(encoding='utf8'))
    counts = collections.defaultdict(collections.Counter)
    for device in snapshot['items']:
        if device['id'] not in registry['items']:
            continue
        public = customer_device(device)
        row = registry['items'][device['id']]
        actual = [v for v in public['views'] if KEY in v.get('spec', {})]
        expected = [v for v in device['views'] if f'{device["id"]}:{v["id"]}' in cache['views']]
        assert len(actual) == len(expected), device['id']
        counts[row['brand']]['measured_views'] += len(actual)
        counts[row['brand']]['items_with_measurements'] += bool(actual)
        counts[row['brand']]['single_view_items_measured'] += len(device['views']) == 1 and bool(actual)
        counts[row['brand']]['total_items_checked'] += 1
    report = {'counts': counts, 'measured_view_references': len(cache['views']), 'removed_on_final_check': removed, 'validation':'Current file hashes, annotation exclusions and customer dimensions checked'}
    report_path = ROOT / 'docs/technical-facts-2026-10-21/cad-measurements-verification.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report), flush=True)

if __name__ == '__main__': main()

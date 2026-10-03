"""Check that the published AI catalog is complete and usable offline."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
CATALOG = ROOT / 'THU_VIEN_THIET_BI_AI_2026'


def load_jsonl(name):
    with (CATALOG / name).open(encoding='utf-8') as source:
        return [json.loads(line) for line in source]


def check():
    manifest = json.loads((CATALOG / 'manifest.json').read_text(encoding='utf-8'))
    records = load_jsonl('equipment_catalog.jsonl')
    groups = load_jsonl('equipment_groups.jsonl')
    assets = load_jsonl('cad_assets.jsonl')
    assert len(records) == manifest['equipment_records']
    assert len(groups) == manifest['product_groups']
    assert len(assets) == manifest['cad_asset_records']
    ids = {r['catalog_id'] for r in records}
    assert len(ids) == len(records)
    assert sum(r['record_type'] == 'priced_variant' for r in records) == sum(manifest['price_rows_by_brand'].values())
    assert sum(r['record_type'] == 'source_cad_device_or_assembly' for r in records) == 641
    assert Counter(r['cad']['status'] for r in records) == manifest['cad_status_counts']
    for group in groups:
        assert group['variant_count'] == len(group['catalog_ids'])
        assert all(item in ids for item in group['catalog_ids'])
    assert sum(g['variant_count'] for g in groups) == len(records)
    for path, expected_hash in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash, path
    for record in records:
        assert (ROOT / record['source_record']['dataset']).is_file(), record['catalog_id']
        assert (ROOT / record['source_record']['table_page']).is_file(), record['catalog_id']
        cad = record['cad']
        for ref in (cad.get('dwg'), cad.get('dxf'), cad.get('preview')):
            if ref:
                assert ref['exists'] and (ROOT / ref['path']).is_file(), (record['catalog_id'], ref)
        for view in cad['views']:
            for ref in (view.get('dxf'), view.get('preview')):
                if ref:
                    assert ref['exists'] and (ROOT / ref['path']).is_file(), (record['catalog_id'], ref)
            if view.get('page'):
                assert (ROOT / view['page'].split('#', 1)[0]).is_file(), (record['catalog_id'], view['page'])
    for asset in assets:
        assert asset['exists'] and (ROOT / asset['path']).is_file(), asset['asset_id']
        assert all(item in ids for item in asset['matched_catalog_ids']), asset['asset_id']
    with sqlite3.connect(CATALOG / 'equipment_catalog.sqlite') as db:
        assert db.execute('SELECT count(*) FROM equipment').fetchone()[0] == len(records)
        assert db.execute('SELECT count(*) FROM cad_assets').fetchone()[0] == len(assets)
        assert db.execute('SELECT count(*) FROM equipment_fts').fetchone()[0] == len(records)
        for query in ('BKN', 'GMC', 'Mitsubishi', 'LA63N'):
            assert db.execute('SELECT count(*) FROM equipment_fts WHERE equipment_fts MATCH ?', (query,)).fetchone()[0] > 0, query
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    page = (CATALOG / 'index.html').read_text(encoding='utf-8')
    assert 'const data=[' in page and 'function render()' in page
    assert 'THU_VIEN_THIET_BI_AI_2026/index.html' in (ROOT / 'index_2026.html').read_text(encoding='utf-8')
    print(json.dumps({'records': len(records), 'groups': len(groups), 'assets': len(assets),
                      'sources': len(manifest['source_sha256']), 'sqlite': 'ok', 'missing_paths': 0}))


if __name__ == '__main__':
    check()

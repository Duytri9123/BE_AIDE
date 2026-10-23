"""Measure each published projection in millimetres, without inferring depth."""
import collections, hashlib, json, logging, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ezdxf
logging.getLogger('ezdxf').setLevel(logging.ERROR)
from ezdxf import bbox, disassemble
from app.services.cad.catalogtb_assets import normalized_source

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / 'data/CatalogTB'
CACHE = ROOT / 'app/data/catalog_customer_cad_measurements.json'
KEY = 'Kích thước mặt CAD ngang×cao (mm)'

def has_annotation_entities(data):
    return bool(re.search(rb'(?m)^[ \t]*0\r?\n(?:DIMENSION|LEADER|MLEADER)\r?$', data))

def measure(path):
    doc = ezdxf.readfile(path)
    if any(e.dxftype() in {'DIMENSION', 'LEADER', 'MLEADER'} for block in doc.blocks for e in block):
        raise ValueError('dimension annotations require separate review')
    if doc.units != 4 or doc.audit().errors:
        raise ValueError('unverified millimetres or DXF audit errors')
    entities = list(disassemble.recursive_decompose(doc.modelspace()))
    if any(e.dxftype() in {'DIMENSION', 'LEADER', 'MLEADER'} for e in entities):
        raise ValueError('dimension annotations require separate review')
    geometry = [e for e in entities if e.dxftype() not in {'TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF', 'POINT', 'VIEWPORT'}]
    extent = bbox.extents(geometry)
    if not extent.has_data or min(extent.size.x, extent.size.y) <= 0:
        raise ValueError('empty or degenerate projection')
    return ' × '.join(format(round(v, 2), 'g') for v in (extent.size.x, extent.size.y))

def cached_view_facts(view_ids, cache=None, device_id=None):
    """Only reuse measurements while the measured source file is unchanged."""
    if cache is None:
        cache = json.loads(CACHE.read_text(encoding='utf8')).get('views', {}) if CACHE.exists() else {}
    result = {}
    for vid in view_ids:
        row = cache.get(f'{device_id}:{vid}') or cache.get(vid)
        if not row:
            continue
        path = CAT / row['path']
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']:
            result[vid] = {KEY: row['value']}
    return result

def main():
    registry_path = ROOT / 'app/data/catalog_customer_technical_facts.json'
    registry = json.loads(registry_path.read_text(encoding='utf8'))
    wanted = {v for row in registry['items'].values() for v in row['view_ids']}
    candidates = collections.defaultdict(set)
    scoped = collections.defaultdict(set)
    for profile in CAT.rglob('thong_tin_thiet_bi.json'):
        raw = json.loads(profile.read_text(encoding='utf-8-sig'))
        if raw.get('browser_hidden'):
            continue
        cid = 'TB-' + hashlib.sha1(profile.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
        for view in raw.get('cad_don', []):
            vid = view.get('id_hinh_goc')
            if vid in wanted and view.get('duong_dan'):
                source = normalized_source(profile.parent / view['duong_dan']).resolve()
                candidates[vid].add(source)
                scoped[(cid, vid)].add(source)
    previous = json.loads(CACHE.read_text(encoding='utf8')).get('views', {}) if CACHE.exists() else {}
    measured, skipped = {}, {}
    requests = [(cid, vid) for cid, row in registry['items'].items() for vid in row['view_ids']]
    for index, (cid, vid) in enumerate(requests):
        paths = scoped.get((cid, vid)) or candidates.get(vid, set())
        cache_key = f'{cid}:{vid}'
        try:
            if not paths:
                raise ValueError('source not found')
            hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            if len(hashes) != 1:
                raise ValueError('ambiguous view identifier')
            path = sorted(paths)[0]; digest = next(iter(hashes))
            old = previous.get(cache_key) or previous.get(vid, {})
            if has_annotation_entities(path.read_bytes()):
                raise ValueError('dimension annotations require separate review')
            value = old['value'] if old.get('sha256') == digest else measure(path)
            measured[cache_key] = {'path': path.relative_to(CAT.resolve()).as_posix(), 'sha256': digest, 'value': value, 'units': 'mm', 'scope': '2D geometry extent; text excluded; not body dimensions or depth'}
        except Exception as exc:
            skipped[cache_key] = str(exc)
        if index % 50 == 0:
            print(f'Measured {index}/{len(requests)}; accepted {len(measured)}; skipped {len(skipped)}', flush=True)
    CACHE.write_text(json.dumps({'version': 1, 'views': measured}, ensure_ascii=False, indent=2), encoding='utf8')
    counts = collections.defaultdict(collections.Counter)
    for cid, row in registry['items'].items():
        facts = cached_view_facts(row['view_ids'], measured, cid)
        for vid in row['view_ids']:
            existing = row.setdefault('view_facts', {}).get(vid, {})
            existing.pop(KEY, None)
            if vid in facts:
                row['view_facts'].setdefault(vid, {}).update(facts[vid])
        counts[row['brand']]['measured_views'] += len(facts)
        counts[row['brand']]['items_with_measurements'] += bool(facts)
        counts[row['brand']]['single_view_items_measured'] += len(row['view_ids']) == 1 and bool(facts)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding='utf8')
    report = {'counts': counts, 'view_references': len(requests), 'measured': len(measured), 'skipped': skipped}
    (ROOT / 'docs/technical-facts-2026-10-21/cad-view-measurements.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(counts), flush=True)

if __name__ == '__main__':
    main()

import sys, io, json, pathlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print('=== TEST 1: inventory + candidates ===')
t0 = time.time()
from app.services.cad.cabinet_templates import candidates, inventory
items = inventory()
elapsed = time.time()-t0
print(f'Inventory: {len(items)} forms ({elapsed:.1f}s)')

dims = {'height':1200.0,'width':800.0,'depth':300.0}
cands = candidates(dims, kind='indoor')
fitting = [c for c in cands if c.get('dimensions') and all(dims[ax] <= c['dimensions'][ax] for ax in dims)]
gen = [c for c in cands if c.get('can_generate')]
print(f'Candidates H1200xW800xD300: {len(cands)} (fitting={len(fitting)}, can_gen={len(gen)})')
for c in (fitting or cands)[:3]:
    d2 = c.get('dimensions') or {}
    cid = c['id'][:40]
    h = d2.get('height',0)
    w = d2.get('width',0)
    d = d2.get('depth',0)
    cg = c.get('can_generate')
    print(f'  {cid:40} H{h:g}xW{w:g}xD{d:g} gen={cg}')

print()
print('=== TEST 2: usable_region 108 forms ===')
from app.services.cad.placement_clearances import usable_region
stats = {}
for item in items:
    for face in (item.get('faces') or []):
        kind = face.get('kind')
        bounds = face.get('clean_bounds')
        if not bounds or kind not in ('mounting_plate','inner_door','outer_door'):
            continue
        stats.setdefault(kind, {'ok':0,'fail':0,'sample_fail':None})
        try:
            usable_region(bounds, item, kind)
            stats[kind]['ok'] += 1
        except Exception as e:
            stats[kind]['fail'] += 1
            if stats[kind]['sample_fail'] is None:
                stats[kind]['sample_fail'] = str(e)[:80]

for kind, st in stats.items():
    total = st['ok'] + st['fail']
    pct = 100*st['ok']//total if total else 0
    print(f'  {kind:20}: {st["ok"]}/{total} ({pct}%) OK')
    if st['sample_fail']:
        print(f'    sample fail: {st["sample_fail"]}')

print()
print('=== TEST 3: calculate_enclosure_specs voi du lieu project 14 ===')
data = json.loads(pathlib.Path('storage/projects/14/cad_review/CAD_layout_review.json').read_text(encoding='utf-8'))
placements = data.get('placements', [])
prop_dims = data.get('proposed_dimensions') or [1200.0, 800.0, 300.0]
# Tao device list don gian tu placements
devices = []
for pl in placements:
    asset_id = pl.get('asset_id') or ''
    if not asset_id:
        continue
    w = float(pl.get('w') or pl.get('width') or 0)
    h = float(pl.get('h') or pl.get('height') or 0)
    tag = pl.get('tag') or '?'
    face = pl.get('mounting_face')
    devices.append({
        'tag': tag,
        'category': pl.get('zone') or 'UNKNOWN',
        'in_a': pl.get('in_a') or 0,
        'poles': pl.get('poles') or 3,
        'quantity': 1,
        'mounting_face': face,
        'owner_face': face,
        'cad': {'asset_id': asset_id},
        'dimensions': {'w': w, 'h': h, 'd': float(prop_dims[2]) if len(prop_dims)>2 else 300},
    })

print(f'Devices tu project 14: {len(devices)}')
try:
    from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
    t0 = time.time()
    spec = EnclosureCadGeneratorService.calculate_enclosure_specs(
        devices, preferred_dimensions=tuple(prop_dims)
    )
    elapsed = time.time()-t0
    fc = spec.get('fit_check', {})
    mr = fc.get('minimum_required', {})
    print(f'OK ({elapsed:.2f}s)')
    print(f'  Min:   H{mr.get("height",0):g}xW{mr.get("width",0):g}xD{mr.get("depth",0):g}')
    print(f'  Chon:  H{spec["height"]:g}xW{spec["width"]:g}xD{spec["depth"]:g}')
    print(f'  Basis: {fc.get("sizing_basis","?")}')
    est = fc.get('estimated_devices', [])
    miss = fc.get('missing_geometry_devices', [])
    print(f'  Uoc luong: {len(est)}, Thieu: {len(miss)}')
except Exception as e:
    import traceback
    print(f'LOI: {e}')
    traceback.print_exc()

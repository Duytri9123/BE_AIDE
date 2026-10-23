"""
Test form selection voi du lieu placement thuc tu project 14.
"""
import sys, io, json, traceback, pathlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Lay du lieu placements tu CAD_layout_review.json
# va chuyen sang format device list cho SourceProjectGenerator
def placements_to_devices(placements, dims):
    """Chuyen danh sach placements -> devices list."""
    devices = []
    for pl in placements:
        asset_id = pl.get('asset_id') or ''
        if not asset_id:
            continue
        cat = str(pl.get('category') or '').upper()
        # Suy loai tu ten/spec neu khong co category
        spec = str(pl.get('original_spec') or pl.get('selected_spec') or '')
        tag = pl.get('tag') or '?'
        w = float(pl.get('w') or pl.get('width') or 0)
        h = float(pl.get('h') or pl.get('height') or 0)
        face = pl.get('mounting_face')
        dev_d = 85.0 if 'MCCB' in (cat or '') else 60.0 if any(k in (cat or '') for k in ('METER', 'LIGHT', 'SW')) else 65.0
        dev = {
            'tag': tag,
            'category': cat or pl.get('zone') or 'UNKNOWN',
            'spec': spec,
            'in_a': pl.get('in_a') or 0,
            'poles': pl.get('poles') or 3,
            'quantity': 1,
            'mounting_face': face,
            'owner_face': face,
            'cad': {'asset_id': asset_id},
            'dimensions': {'w': w, 'h': h, 'd': dev_d},
        }
        devices.append(dev)
    return devices

# Load project 14 data
print('='*60)
print('LOAD DU LIEU PROJECT 14 (MEP JOSEON CO.OP)')
print('='*60)
data_path = pathlib.Path('storage/projects/14/cad_review/CAD_layout_review.json')
data = json.loads(data_path.read_text(encoding='utf-8'))
placements = data.get('placements', [])
dims = data.get('proposed_dimensions') or [1200.0, 800.0, 300.0]
enclosure_src = data.get('enclosure_source', {})

print(f'Proposed dims: H{dims[0]:g}xW{dims[1]:g}xD{dims[2]:g}')
print(f'Placements: {len(placements)}')
print(f'Enclosure source: {enclosure_src.get("template_id")} / {enclosure_src.get("source")}')
print()

devices = placements_to_devices(placements, dims)
print(f'Devices chuyen doi: {len(devices)}')

# Kiem tra devices co asset_id tb: 
tb_count = sum(1 for d in devices if str((d.get('cad') or {}).get('asset_id','')).startswith('tb:'))
print(f'  Co asset_id tb:: {tb_count}')
for d in devices[:5]:
    face = d.get('mounting_face', '?')
    asset = str((d.get('cad') or {}).get('asset_id', ''))[:30]
    w = (d.get('dimensions') or {}).get('w', 0)
    h = (d.get('dimensions') or {}).get('h', 0)
    print(f"  {d['tag']:8} {d['category']:12} face={str(face):15} asset={asset:30} w={w} h={h}")

# TEST 1: cabinet_templates.candidates
print('\n' + '='*60)
print('TEST 1: cabinet_templates.candidates()')
print('='*60)
try:
    from app.services.cad.cabinet_templates import candidates, inventory
    items = inventory()
    dim_dict = {'height': dims[0], 'width': dims[1], 'depth': dims[2]}
    cands = candidates(dim_dict, kind='indoor')
    fitting = [c for c in cands if c.get('dimensions') and all(
        dim_dict[ax] <= c['dimensions'][ax] for ax in dim_dict)]
    gen = [c for c in cands if c.get('can_generate')]
    print(f'OK - Tong forms indoor: {sum(1 for i in items if i.get("kind")=="indoor")}')
    print(f'  Candidates cho {dim_dict}: {len(cands)}')
    print(f'  Fitting (>= dims): {len(fitting)}')
    print(f'  Can generate:      {len(gen)}')
    print(f'  Top 3:')
    for c in (fitting or cands)[:3]:
        d2 = c.get('dimensions') or {}
        print(f"    {c['id'][:40]:40} H{d2.get('height',0):g}xW{d2.get('width',0):g}xD{d2.get('depth',0):g}"
              f"  fit={c.get('exact')} gen={c.get('can_generate')}")
except Exception as e:
    print(f'LOI: {e}')
    traceback.print_exc()

# TEST 2: usable_region voi form thuc
print('\n' + '='*60)
print('TEST 2: placement_clearances.usable_region() - tat ca 108 forms')
print('='*60)
try:
    from app.services.cad.cabinet_templates import inventory
    from app.services.cad.placement_clearances import usable_region
    items = inventory()
    face_stats = {}
    for item in items:
        for face in (item.get('faces') or []):
            kind = face.get('kind')
            bounds = face.get('clean_bounds')
            if not bounds or kind not in ('mounting_plate', 'inner_door', 'outer_door'):
                continue
            if kind not in face_stats:
                face_stats[kind] = {'ok': 0, 'fail': 0}
            try:
                usable_region(bounds, item, kind)
                face_stats[kind]['ok'] += 1
            except Exception:
                face_stats[kind]['fail'] += 1
    print('Ket qua tren 108 forms:')
    for kind, stats in face_stats.items():
        total = stats['ok'] + stats['fail']
        print(f"  {kind:20}: {stats['ok']}/{total} thanh cong "
              f"({100*stats['ok']//total if total else 0}%)")
except Exception as e:
    print(f'LOI: {e}')
    traceback.print_exc()

# TEST 3: enclosure sizing voi fallback
print('\n' + '='*60)
print('TEST 3: calculate_enclosure_specs() voi fallback estimation')
print('='*60)
spec = None
try:
    from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
    t0 = time.time()
    spec = EnclosureCadGeneratorService.calculate_enclosure_specs(
        devices,
        preferred_dimensions=tuple(dims)
    )
    elapsed = time.time() - t0
    fc = spec.get('fit_check', {})
    mr = fc.get('minimum_required', {})
    print(f'OK - {elapsed:.2f}s')
    print(f'  Min:   H{mr.get("height",0):g}xW{mr.get("width",0):g}xD{mr.get("depth",0):g} mm')
    print(f'  Chon:  H{spec["height"]:g}xW{spec["width"]:g}xD{spec["depth"]:g} mm')
    print(f'  Basis: {fc.get("sizing_basis","?")}')
    estimated = fc.get('estimated_devices', [])
    missing = fc.get('missing_geometry_devices', [])
    if estimated:
        print(f'  Uoc luong ({len(estimated)}): {", ".join(estimated[:8])}')
    if missing:
        print(f'  Thieu ({len(missing)}): {", ".join(missing[:5])}')
except Exception as e:
    print(f'LOI: {e}')
    traceback.print_exc()

# TEST 4: SourceProjectGenerator.generate() - MAIN TEST
print('\n' + '='*60)
print('TEST 4: SourceProjectGenerator.generate() - tao CAD layout thu')
print('='*60)
try:
    from app.services.cad.source_project_generator import SourceProjectGenerator
    use_dims = (spec['height'], spec['width'], spec['depth']) if spec else tuple(dims)
    print(f'  Yeu cau: H{use_dims[0]:g}xW{use_dims[1]:g}xD{use_dims[2]:g} mm')
    t0 = time.time()
    result = SourceProjectGenerator.generate(
        project_id=99999,
        output_dir='storage/projects',
        dimensions=use_dims,
        devices=devices,
        kind='indoor',
        product_name='TEST_JOSEON_NGUYEN_TRAI',
        allow_partial=True,
    )
    elapsed = time.time() - t0
    actual = result['dimensions']
    pl = result['placements']
    unmatched = result['unmatched_devices']
    print(f'OK - {elapsed:.1f}s')
    print(f'  Template: {result["template_id"]}')
    print(f'  Source:   {result["source"]}')
    print(f'  Kich thuoc: H{actual["height"]:g}xW{actual["width"]:g}xD{actual["depth"]:g}')
    print(f'  Placements: {len(pl)} thiet bi dat duoc')
    print(f'  Unmatched:  {len(unmatched)} chua co CAD')
    print(f'  Status:     {result["status"]}')
    print(f'  File:       {result["path"]}')
    # Phan tich bo tri tren cac mat
    faces_used = {}
    for p in pl:
        f = p.get('mounting_face', 'unknown')
        faces_used[f] = faces_used.get(f, 0) + 1
    print(f'  Bo tri theo mat: {faces_used}')
    if pl:
        print(f'  Mau 3 vi tri dau:')
        for p in pl[:3]:
            t2 = str(p.get('tag', '?'))
            f2 = str(p.get('mounting_face', '?'))
            x2, y2, w2, h2 = p.get('x',0), p.get('y',0), p.get('width',0), p.get('height',0)
            print(f"    {t2:8} {f2:15} x={x2:.0f} y={y2:.0f} w={w2:.0f} h={h2:.0f}")
    if result.get('form_fit_attempts'):
        print(f'  Forms thu ({len(result["form_fit_attempts"])}):')
        for att in result['form_fit_attempts'][:3]:
            print(f"    {att['template_id'][:35]}: {att['reason'][:60]}")
except Exception as e:
    print(f'LOI: {e}')
    traceback.print_exc()

print('\n' + '='*60)
print('HOAN THANH')
print('='*60)

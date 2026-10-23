"""TEST 4: SourceProjectGenerator.generate() voi du lieu project 14."""
import sys, io, json, traceback, pathlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load data project 14
data = json.loads(pathlib.Path('storage/projects/14/cad_review/CAD_layout_review.json').read_text(encoding='utf-8'))
placements = data.get('placements', [])
prop_dims = data.get('proposed_dimensions') or [1200.0, 800.0, 300.0]

# Build devices
devices = []
for pl in placements:
    asset_id = pl.get('asset_id') or ''
    if not asset_id:
        continue
    w = float(pl.get('w') or pl.get('width') or 0)
    h = float(pl.get('h') or pl.get('height') or 0)
    face = pl.get('mounting_face')
    devices.append({
        'tag': pl.get('tag') or '?',
        'category': pl.get('zone') or 'UNKNOWN',
        'in_a': pl.get('in_a') or 0,
        'poles': pl.get('poles') or 3,
        'quantity': 1,
        'mounting_face': face,
        'owner_face': face,
        'cad': {'asset_id': asset_id},
        'dimensions': {'w': w, 'h': h, 'd': float(prop_dims[2]) if len(prop_dims) > 2 else 300},
    })

print(f'Devices: {len(devices)}')
dims_tuple = (float(prop_dims[0]), float(prop_dims[1]), float(prop_dims[2]))
print(f'Kich thuoc yeu cau: H{dims_tuple[0]:g}xW{dims_tuple[1]:g}xD{dims_tuple[2]:g}')
print()

print('=== TEST 4: SourceProjectGenerator.generate() ===')
try:
    from app.services.cad.source_project_generator import SourceProjectGenerator
    t0 = time.time()
    result = SourceProjectGenerator.generate(
        project_id=99999,
        output_dir='storage/projects',
        dimensions=dims_tuple,
        devices=devices,
        kind='indoor',
        product_name='TEST_JOSEON_NGUYEN_TRAI',
        allow_partial=True,
    )
    elapsed = time.time() - t0
    actual = result['dimensions']
    pl_list = result['placements']
    unmatched = result['unmatched_devices']
    print(f'OK - {elapsed:.1f}s')
    print(f'  Template:   {result["template_id"]}')
    print(f'  Source DXF: {result["source"]}')
    print(f'  Kich thuoc: H{actual["height"]:g}xW{actual["width"]:g}xD{actual["depth"]:g}')
    print(f'  Placements: {len(pl_list)} thiet bi dat duoc')
    print(f'  Unmatched:  {len(unmatched)} chua co CAD')
    print(f'  Status:     {result["status"]}')
    print(f'  Release:    {result.get("release_ready")}')
    print(f'  File:       {result["path"]}')

    # Phan tich bo tri theo mat
    faces_used = {}
    for p in pl_list:
        f = p.get('mounting_face', 'unknown')
        faces_used[f] = faces_used.get(f, 0) + 1
    print(f'  Mat bo tri: {faces_used}')

    # Kiem tra can giua
    if pl_list:
        print()
        print('  Vi tri thiet bi (tat ca):')
        for p in pl_list:
            tag = str(p.get('tag', '?'))
            face = str(p.get('mounting_face', '?'))
            x = p.get('x', 0)
            y = p.get('y', 0)
            w = p.get('width', 0)
            h = p.get('height', 0)
            print(f'    {tag:8} {face:15} x={x:.0f} y={y:.0f} w={w:.0f} h={h:.0f}')

    # Form fit attempts
    if result.get('form_fit_attempts'):
        print()
        print(f'  Forms thu ({len(result["form_fit_attempts"])}):')
        for att in result['form_fit_attempts'][:5]:
            print(f'    {att["template_id"][:35]}: {att["reason"][:70]}')

except Exception as e:
    print(f'LOI: {e}')
    traceback.print_exc()

print()
print('=== HOAN THANH ===')

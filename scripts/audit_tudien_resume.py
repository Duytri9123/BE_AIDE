"""Audit cross-references after resuming the cabinet library pipeline."""
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'data/tudien'

def load(relative):
    return json.loads((OUT / relative).read_text(encoding='utf-8'))

def save(relative, value):
    (OUT / relative).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

profiles = load('geometry_profiles.json')
ids = {g['id'] for g in profiles}
errors = []
checks = 0

def check_path(relative):
    global checks
    checks += 1
    if not (OUT / relative).is_file():
        errors.append({'missing_file': relative})

def check_id(gid, context):
    global checks
    checks += 1
    if gid not in ids:
        errors.append({'missing_geometry': gid, 'context': context})

for g in profiles:
    check_path(g['cad_views']['source_view'])
for key, family in load('family_index.json').items():
    check_path('thiet_bi/' + key + '/family.json')
    for gid in family['geometry_profile_ids']:
        check_id(gid, key)
        check_path('thiet_bi/' + key + '/cad/' + gid + '.dxf')
for sku in load('sku_registry.json'):
    for gid in sku.get('candidate_geometry_profile_ids', []):
        check_id(gid, sku['id'])
    if sku.get('geometry_profile_id'):
        check_id(sku['geometry_profile_id'], sku['id'])
for frame in load('form_tu/frames.json'):
    check_path(frame['path'])
    check_path('form_tu/' + frame['source_id'] + '/source_form.dxf')
    check_path(str(Path(frame['path']).parent / 'preview.svg'))
    for placement in load(frame['path'])['placements']:
        if placement.get('geometry_profile_id'):
            check_id(placement['geometry_profile_id'], frame['id'])
for media in load('embedded_media.json'):
    check_path(media['path'])
validation = load('validation.json')
review = load('review_queue.json')
review['geometry_transform_differences'] = validation['geometry_transform_bound_differences']
save('review_queue.json', review)
report = {
    'checked_at': datetime.now(timezone.utc).isoformat(),
    'source_directory': str(OUT.parents[2] / 'Tudien'),
    'output_directory': str(OUT),
    'reference_checks': checks,
    'errors': errors,
    'source_files_checked': validation['source_files_checked'],
    'geometry_files_checked': validation['geometry_files_checked'],
    'geometry_transform_differences': len(validation['geometry_transform_bound_differences']),
    'policy': 'Use current JSON indices. Historical unindexed files remain preserved. Transform differences and unverified SKU mappings require source review before production use.',
}
save('resume_audit.json', report)
with (OUT / 'README.md').open('a', encoding='utf-8') as stream:
    stream.write('\n## Kiểm tra khi tiếp tục tiến trình\n\n'
                 f"Đã kiểm tra lại {report['source_files_checked']} tệp nguồn, "
                 f"{report['geometry_files_checked']} file geometry và {checks} tham chiếu. "
                 f"Lỗi tham chiếu: {len(errors)}. "
                 f"Còn {report['geometry_transform_differences']} vị trí sai lệch bao hình sau chuyển đổi; "
                 'xem `validation.json` và `review_queue.json` trước khi tái sử dụng. '
                 'Tra cứu bằng các chỉ mục JSON hiện tại hoặc `index.html`; các file lịch sử chưa còn trong chỉ mục được giữ để đối chiếu.\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))

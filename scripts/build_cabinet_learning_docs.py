"""Build read-only source inventories and review dossiers; never approve geometry."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def build(backend, legacy, output):
    shell_dir = backend / 'data/CatalogTB/Form tủ'
    block_dir = backend / 'data/device_layouts/formtu'
    catalog = read(shell_dir / 'catalog.json')
    blocks = read(block_dir / 'manifest.json')
    legacy_manifest = legacy / 'manifest.json'
    old = read(legacy_manifest) if legacy_manifest.is_file() else {'items': []}
    resize = read(shell_dir / 'resize_profiles.json')
    output.mkdir(parents=True, exist_ok=True)
    dossiers = output / 'ho_so_mau'
    dossiers.mkdir(exist_ok=True)
    records, missing = [], []

    def artifact(base, relative):
        if not relative:
            return None
        path = (base / relative).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError(f'Path escapes source directory: {relative}')
        exists = path.is_file()
        if not exists:
            missing.append(str(path))
        return {'path': str(path), 'exists': exists, 'sha256': digest(path)}

    def append(namespace, item_id, **fields):
        record = {'record_id': f'{namespace}:{item_id}', 'namespace': namespace,
                  'source_id': item_id, 'training_eligible': False,
                  'fabrication_approved': False, **fields}
        records.append(record)
        return record

    for shell in catalog['shells']:
        assets = {k: artifact(shell_dir, shell.get(k)) for k in
                  ('source_dxf', 'preview', 'layout_analysis_json', 'copper_reference_json')}
        layout_asset = assets['layout_analysis_json']
        layout = read(Path(layout_asset['path'])) if layout_asset and layout_asset['exists'] else {}
        copper_asset = assets['copper_reference_json']
        copper = read(Path(copper_asset['path'])) if copper_asset and copper_asset['exists'] else {}
        occurrences = [{k: occurrence.get(k) for k in
                        ('source_handle', 'block_name', 'role', 'insertion_point_source',
                         'rotation_deg', 'scale', 'identification_basis')}
                       for occurrence in layout.get('layout_occurrences', [])]
        boundary = shell.get('source_boundary_reconciliation') or {}
        unresolved = (shell.get('remaining_block_review') or {}).get('retained_unidentified_blocks', [])
        flags = ['requires_engineering_review', 'requires_source_unit_and_face_verification']
        if shell.get('verified_form') is None:
            flags.append('separation_form_not_verified')
        if unresolved:
            flags.append('unidentified_geometry_retained')
        if any(not f.get('has_source_boundary') for f in boundary.get('faces', [])):
            flags.append('some_labelled_views_have_no_verified_boundary')
        if not boundary.get('electrical_residue_review_complete'):
            flags.append('electrical_residue_review_incomplete')
        record = append('project_shell', shell['id'], name=shell['name'],
                        dimensions_mm=shell.get('dimensions_mm'),
                        material=shell.get('material_from_source'),
                        source_specification=shell.get('source_specification'),
                        sheet_thickness_mm=shell.get('sheet_thickness_mm'),
                        source_sheet_handle=shell.get('source_handle'),
                        catalog_source=str(shell_dir / 'catalog.json'), assets=assets,
                        faces=shell.get('faces', []),
                        boundary_reconciliation=boundary,
                        resize_profile=resize.get(shell['id']),
                        verified_form=shell.get('verified_form'),
                        separation_review=shell.get('separation_review'),
                        review_status=shell.get('review_status'),
                        reuse_decision=shell.get('reuse_decision'),
                        occurrences=occurrences,
                        occurrence_count_policy=layout.get('count_policy'),
                        copper_reference={'reference_only': copper.get('reference_only'),
                                          'verified_material': copper.get('verified_material'),
                                          'route_candidates': copper.get('route_candidates', []),
                                          'must_recheck': copper.get('must_recheck')},
                        review_flags=flags)
        lines = [f"# {shell['name']}", '', f"Mã nguồn: `{record['record_id']}`.", '',
                 'Trạng thái: tham khảo cần rà soát; chưa đủ điều kiện làm nhãn thiết kế đúng hoặc duyệt chế tạo.', '',
                 '## Kích thước và kết cấu nguồn', '',
                 f"Kích thước ghi nguồn H W D theo mm: `{json.dumps(record['dimensions_mm'], ensure_ascii=False)}`.", '',
                 f"Vật liệu: {record['material']}. Form phân khoang xác minh: `{record['verified_form']}`.", '',
                 '## Các tệp bằng chứng', '', '| Nội dung | Tệp nguồn | Có tệp |', '| --- | --- | --- |']
        for key, asset in assets.items():
            if asset:
                url = Path(asset['path']).as_posix()
                lines.append(f"| {key} | [Mở nguồn](<{url}>) | {asset['exists']} |")
        lines += ['', 'SHA256 từng tệp, hình học tuyến tham khảo và hồ sơ phân khoang được lưu trong `source_inventory.jsonl` theo mã nguồn trên.', '',
                  '## Mặt và mốc hình học', '', '| Mặt nguồn | Loại | Handle nhãn | Handle đường bao |', '| --- | --- | --- | --- |']
        for face in record['faces']:
            lines.append(f"| {face.get('source_label', '')} | {face.get('kind', '')} | {face.get('source_label_handle', '')} | {face.get('source_perimeter_handle') or 'Chưa xác minh'} |")
        lines += ['', '## Chi tiết xuất hiện trong bố trí gốc', '',
                  'Mỗi dòng là một lần xuất hiện trên CAD. Nhiều hình chiếu có thể cùng một chi tiết vật lý; số dòng không phải số lượng BOM.', '',
                  '| Handle | Block | Vai trò nhận diện nguồn |', '| --- | --- | --- |']
        for occurrence in occurrences:
            name = str(occurrence.get('block_name', '')).replace('|', '\\|')
            lines.append(f"| {occurrence.get('source_handle', '')} | {name} | {occurrence.get('role', '')} |")
        lines += ['', '## Mục cần xác minh trước khi tái sử dụng', '']
        lines += [f'- `{flag}`.' for flag in flags]
        lines += ['', 'Đối chiếu thêm mốc gá, lỗ gá, khoảng sau cánh, quỹ đạo cánh, đầu cos và tuyến cáp theo đúng model. Việc có profile resize chỉ xác nhận có dữ liệu biến đổi, không duyệt cơ khí.', '',
                  'Hướng dẫn kiểm tra từng nhóm chi tiết: [Chi tiết và bằng chứng](../02_CHI_TIET_VA_BANG_CHUNG.md).', '']
        (dossiers / f"{shell['id']}.md").write_text('\n'.join(lines), encoding='utf8')

    for item in old['items']:
        append('legacy_formtu_shell', item['id'], source_file=item.get('source_file'),
               source_handle=item.get('source_handle'), source_block=item.get('source_block'),
               dimensions_as_recorded=item.get('dimensions'), kind=item.get('kind'),
               kind_basis=item.get('kind_basis'), labels=item.get('labels'),
               stretch_dimensions=item.get('stretch_dimensions'),
               source_dxf=artifact(legacy, item.get('filename')),
               review_flags=['legacy_source_not_equivalent_to_project_shell',
                             'requires_units_dimensions_and_mechanical_review'])
    for item in blocks['items']:
        append('formtu_block', item['id'], name=item.get('name'),
               source_file=item.get('source_file'), source_block=item.get('source_block'),
               brand=item.get('brand'), brand_basis=item.get('brand_basis'),
               model_verified=item.get('model_verified'), view=item.get('view'),
               width_as_recorded=item.get('width'), height_as_recorded=item.get('height'),
               width_mm=item.get('width_mm'), height_mm=item.get('height_mm'),
               source_units=item.get('source_units'), units=item.get('units'),
               geometry_fingerprint=item.get('geometry_fingerprint'),
               manifest_geometry_sha256=item.get('geometry_sha256'),
               source_dxf=artifact(block_dir, item.get('filename')),
               review_flags=['requires_verified_model_view_and_unit_conversion'])
    for item in catalog.get('excluded_shells', []):
        append('excluded_project_shell', item['id'], name=item.get('name'),
               review_flags=['excluded_from_active_catalog'],
               exclusion_source=str(shell_dir / 'form_source_exclusions.json'))

    ids = [row['record_id'] for row in records]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate namespaced source IDs')
    (output / 'source_inventory.jsonl').write_text(
        ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in records), encoding='utf8')
    source_paths = [shell_dir / 'catalog.json', shell_dir / 'resize_profiles.json',
                    block_dir / 'manifest.json', legacy_manifest]
    stats = {
        'schema_version': 1, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'metadata_and_file_integrity_not_visual_or_engineering_approval',
        'source_manifests': [{'path': str(p), 'sha256': digest(p)} for p in source_paths],
        'legacy_manifest_available': legacy_manifest.is_file(),
        'counts': dict(Counter(row['namespace'] for row in records)),
        'total_records': len(records), 'missing_files': sorted(set(missing)),
        'active_shells_auto_select_true': sum(s.get('auto_select') is True for s in catalog['shells']),
        'active_shells_verified_form': sum(s.get('verified_form') is not None for s in catalog['shells']),
        'active_shells_with_resize_profile': sum(s['id'] in resize for s in catalog['shells']),
        'shells_with_unidentified_geometry': sum('unidentified_geometry_retained' in r.get('review_flags', []) for r in records),
        'block_unit_labels': dict(Counter(str(x.get('units')) for x in blocks['items'])),
        'blocks_model_verified': sum(x.get('model_verified') is True for x in blocks['items']),
        'blocks_missing_mm_dimensions': sum(x.get('width_mm') is None or x.get('height_mm') is None for x in blocks['items']),
        'legacy_kind_labels': dict(Counter(x.get('kind', 'unknown') for x in old['items'])),
        'review_only': True, 'training_eligible_records': 0,
    }
    write_json(output / 'audit_summary.json', stats)
    lines = ['# Danh mục hồ sơ từng mẫu vỏ tủ', '',
             'Hồ sơ sinh từ catalog hiện tại. Kích thước là thông tin ghi trong nguồn; mọi mẫu vẫn cần kiểm tra cơ khí.', '',
             '| Mã | Tên và hồ sơ |', '| --- | --- |']
    for s in catalog['shells']:
        lines.append(f"| `{s['id']}` | [{s['name']}](ho_so_mau/{s['id']}.md) |")
    (output / 'DANH_MUC_MAU.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-formtu', type=Path, default=Path('D:/data/cabinet_templates/formtu'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    build(backend, args.legacy_formtu, args.output or backend / 'docs/cabinet-design-learning')

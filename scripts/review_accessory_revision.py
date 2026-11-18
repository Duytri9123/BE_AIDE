"""Apply the individual, hash-bound review of the 157 pending source profiles.

This changes identity, classification, projection evidence and discovery indices.
It never alters supplier geometry, prices, chosen electrical variants or standards
approval. A reference in the CAD library is not a released purchasing selection.
"""
import hashlib
import json
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from scripts.import_accessory_revision import CAT, read, write, refresh_discovery
from app.services.catalog_publication_policy import public_profile_allowed
from app.services.catalog_source_identification import source_fingerprint

REVIEW = BACKEND / 'app/data/accessory_revision_review_20261118.json'
FOLDER = CAT / 'NguonCapNhat/20261118_a72a95b79f48'
BACKUP = BACKEND / 'tmp/runtime/pending-157-review/before_review'
FACE_OVERRIDES = {
    'REV20261118-674812': 'Mặt bên',
    'REV20261118-4B4F47': 'Mặt bên',
    'REV20261118-42FDCD': 'Mặt bên',
    'REV20261118-7D93AD': 'Mặt bên',
    'REV20261118-A8417': 'Chỉ dẫn và nhãn nguồn',
}
COUNTS = {'REV20261118-3E609D': 5, 'REV20261118-7ED098': 2,
          'REV20261118-7ED0A0': 1, 'REV20261118-7ED0A8': 1, 'REV20261118-7ED0B8': 1}
SELECTION_PENDING = {5, 16, 18, 19, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
    42, 44, 47, 56, 60, 78, 79, 80, 81, 86, 87, 88, 89, 91, 93, 94, 95, 104,
    105, 107, 108, 110, 116, 118, 119, 120, 123, 125, 126, 127, 135, 141, 147, 148, 155, 156}
SELECTION_PENDING.update({6, 54, 55, 64, 65, 66, 67, 68, 75})
MEASUREMENT = {7: 'voltage', 10: 'current', 44: 'voltage', 76: 'voltage'}
MECHANICAL = {'LIFTING_ATTACHMENT', 'CABINET_LOCK', 'HINGE', 'CABINET_HANDLE',
    'VENT_FILTER', 'CONTROL_BOX', 'INSULATING_SUPPORT', 'MOUNTING_SUPPORT',
    'MECHANICAL_PART', 'CABLE_LUG', 'OPERATING_HANDLE', 'FAN_GUARD', 'BRAND_MARK'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog_id(path):
    return 'TB-' + hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]


def validate_review(data):
    assert len(data['items']) == 157
    assert sha(FOLDER / 'source.dwg') == data['source_sha256']
    for row in data['items']:
        path = (CAT / row['profile']).resolve()
        assert path.is_relative_to(CAT.resolve()) and path.is_file()
        for view in row['views']:
            drawing = (CAT / view['path']).resolve()
            assert drawing.is_relative_to(CAT.resolve())
            assert sha(drawing) == view['dxf_sha256'], view['path']
            assert sha(drawing.with_name('xem_truoc.svg')) == view['preview_sha256'], view['path']


def backup(data):
    BACKUP.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(CAT / '_agent_index/equipment_catalog.sqlite') as db:
        if not (BACKUP / 'equipment_catalog.sqlite').exists():
            with sqlite3.connect(BACKUP / 'equipment_catalog.sqlite') as target:
                db.backup(target)
    files = ['ai_library_manifest.json', 'ai_device_index.json', 'index.html',
             '_agent_index/browser_display_v6.json', '_agent_index/equipment_catalog.jsonl',
             '_agent_index/manifest.json'] + [row['profile'] for row in data['items']]
    for relative in files:
        source = CAT / relative
        target = BACKUP / 'CatalogTB' / relative
        if source.is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for name in ('library_manufacturer_evidence.json', 'catalog_source_identification.json',
                 'catalogtb_published_information.json'):
        source = BACKEND / 'app/data' / name
        target = BACKUP / name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)


def profile_review(row, profile):
    n = row['n']
    profile['ten_kieu'] = profile['ten_san_pham'] = row['display']
    profile['ma_dong_san_pham'] = row['model']
    profile['ban_chat'] = row['category']
    profile['catalog_information_type'] = row['generic_identity'] or row['category']
    profile['auto_select'] = False
    profile['needs_review'] = True
    profile['muc_do_xac_nhan'] = 'Đã kiểm tra danh tính và hình nguồn; CAD tham khảo, chưa duyệt cấu hình điện hoặc chế tạo.'
    ai = profile.setdefault('nhan_dien_ai', {})
    ai.update(loai_thiet_bi_code=row['category'], tu_dong_chon_theo_vai_tro=False,
              fabrication_ready=False, ma_dat_hang_da_chon=None)
    if n in MEASUREMENT:
        ai['measurement_function'] = MEASUREMENT[n]
    elif n == 134:
        ai.pop('measurement_function', None)
    if row['brand']:
        profile['hang_xac_nhan'] = None if row['brand_candidate_only'] else row['brand']
        profile['nhan_dien_web'] = {**(profile.get('nhan_dien_web') or {}),
            'brand_candidate': row['brand'],
            'status': 'candidate_from_reviewed_source_and_family' if row['brand_candidate_only'] else 'source_brand_label_reviewed',
            'review_date': '2026-11-18', 'identification_basis': row['note'],
            'exact_sku_verified': False}
    elif profile.get('import_revision'):
        profile['hang_xac_nhan'] = None
        profile.pop('nhan_dien_web', None)
    profile['tu_khoa_tim_kiem'] = list(dict.fromkeys([
        *(profile.get('tu_khoa_tim_kiem') or []), row['source_name'], row['display'],
        row['category'], row['model'], *([row['brand']] if row['brand'] else [])]))
    profile['cong_dung'] = row['display'] + '. ' + row['note']
    review = {'reviewed_on': '2026-11-18', 'status': row['mode'],
        'source_name': row['source_name'], 'note': row['note'],
        'brand_basis': 'candidate' if row['brand_candidate_only'] else 'source_label' if row['brand'] else 'generic_mechanical' if row['generic_identity'] else 'unresolved',
        'observed_texts': row['observed_texts'], 'source_context': row['source_context'],
        'manufacturer_documents': row['documents'], 'ordering_code_verified': False,
        'electrical_configuration_verified': False, 'fabrication_ready': False,
        'required_before_project_selection': ['Mã và cấu hình đầy đủ', 'Tài liệu lắp/đấu đúng mã',
            'Mốc gá và bao hình theo mặt', 'Thông số điện theo yêu cầu dự án']}
    profile['source_identity_review_20261118'] = review
    if row.get('research_followup'):
        review['research_followup'] = row['research_followup']
    if row['category'] not in MECHANICAL:
        profile.setdefault('yeu_cau_chon_day', {
            'vai_tro_ket_noi': ['Theo sơ đồ cọc và chức năng của mã được chọn'],
            'tiet_dien_mac_dinh_mm2': None,
            'quy_tac': 'Chọn theo đầu nối, tải và tài liệu mã đầy đủ; không suy từ hình CAD.',
            'vat_lieu_va_kieu': [], 'can_kiem_tra': ['Sơ đồ cọc đúng mã', 'Giới hạn đầu nối', 'Tuyến và chiều dài']})
    viewed = {v['id']: v for v in row['views']}
    for entry in profile['cad_don']:
        evidence = viewed.get(entry['id_hinh_goc'])
        if not evidence:
            continue
        vid = entry['id_hinh_goc']
        face = FACE_OVERRIDES.get(vid, row['face'])
        entry['huong_nhin'] = face
        entry['nhan_hien_thi'] = face + ' · ' + vid
        entry['nhan_dien_mat'] = {'method': 'individual_source_visual_review',
            'reviewed_on': '2026-11-18', 'dxf_sha256': evidence['dxf_sha256'],
            'preview_sha256': evidence['preview_sha256'], 'basis': row['note']}
        entry['bien_the_cad'] = vid
        body = row['mode'] == 'publish_reference' and n not in SELECTION_PENDING
        body = body and face in {'Mặt trước', 'Mặt bên', 'Mặt trên', 'Mặt sau'}
        entry['bo_tri_trong_tu'] = {'cho_phep_chen': bool(body),
            'huong_dan': 'Tham khảo bố trí đúng mặt nguồn; chưa xác nhận cấu hình điện, ghép mặt hoặc gia công.'}
        entry['asset_role'] = 'source_reference'
        if row['category'] in {'MOUNTING_SUPPORT', 'MECHANICAL_PART', 'CONTROL_BOX'}:
            entry['asset_role'] = 'mounting_reference'
        if row['mode'] in {'design_reference', 'envelope_only', 'graphic_reference'}:
            entry['asset_role'] = row['mode']
        if vid == 'REV20261118-A8417':
            entry['asset_role'] = 'source_annotation'
        entry['physical_units_in_source_view'] = COUNTS.get(vid,
            3 if n in {90, 93, 94, 95, 157} else 2 if n == 106 else 1)
        entry['kiem_tra_net_cad'] = {**(entry.get('kiem_tra_net_cad') or {}),
            'status': 'source_geometry_visually_reviewed', 'fabrication_ready': False}
    if n == 13:
        preferred = next(v for v in profile['cad_don'] if v['id_hinh_goc'] == 'REV20261118-4284C9')
        profile['cad_chen_tu'] = {k: preferred[k] for k in ('id_hinh_goc', 'huong_nhin', 'duong_dan')}
    else:
        primary = (profile.get('cad_chen_tu') or {}).get('id_hinh_goc')
        preferred = next((v for v in profile['cad_don'] if v['id_hinh_goc'] == primary), None)
        if preferred and primary in viewed:
            profile['cad_chen_tu']['huong_nhin'] = preferred['huong_nhin']
    profile['quy_tac_ghep_mat'] = {'auto_pair': False,
        'note': 'Các trạng thái nguồn không tự ghép thành các mặt của cùng một mã; số CAD không phải số thiết bị.'}
    if n in {90, 93, 94, 95, 157}:
        profile['cau_truc_cum'] = {'physical_units_per_cad': 3,
            'basis': 'Ba mô-đun/cửa sổ riêng trong hình nguồn; không chốt thông số điện.'}
    if n in {88, 89, 91}:
        profile['cau_truc_cum'] = {'physical_units_per_cad': 1,
            'contains_socket': True, 'socket_model_verified': False,
            'note': 'Một cụm rơ-le với đế; không đếm đế thành rơ-le thứ hai.'}
    if n == 92:
        profile['cau_truc_cum'] = {'physical_units_per_cad': 1,
            'count_varies_by_view': True, 'auto_takeoff': False}
    if n == 106:
        profile['cau_truc_cum'] = {'physical_units_per_cad': 2,
            'roles_verified': False, 'note': 'Hai thanh nguồn; chưa gán riêng N/PE.'}
    if n == 141:
        profile['cau_truc_cum'] = {'physical_units_per_cad': 1,
            'unit_of_count': 'source_assembly', 'terminal_count_verified': False,
            'auto_takeoff': False}
    profile.pop('browser_hidden', None)
    return profile


def main():
    data = read(REVIEW)
    validate_review(data)
    backup(data)
    evidence_path = BACKEND / 'app/data/library_manufacturer_evidence.json'
    maker_evidence = read(evidence_path)
    maker_rows = maker_evidence.setdefault('evidence', {})
    overlay_path = BACKEND / 'app/data/catalogtb_published_information.json'
    overlay = read(overlay_path)
    overlay_rows = overlay.setdefault('profiles', {})
    paths, outcomes = set(), []
    for row in data['items']:
        path = CAT / row['profile']
        profile = profile_review(row, read(path))
        cid = catalog_id(path)
        if row['brand']:
            maker_rows[cid] = {'brand': row['brand'],
                'status': 'manufacturer_candidate_reviewed' if row['brand_candidate_only'] else 'manufacturer_label_reviewed',
                'note': row['note'], 'reviewed_on': '2026-11-18',
                'views': [{'view_id': v['id'], 'sha256': v['dxf_sha256']} for v in row['views']],
                'library_description': {'display': row['display'], 'type': row['category'],
                    'product_code': row['model'], 'use': profile['cong_dung']}}
        overlay_rows[cid] = {**overlay_rows.get(cid, {}),
            'ten_san_pham': row['display'], 'ma_dong_san_pham': row['model'],
            'catalog_information_type': row['generic_identity'] or row['category']}
        # Publication is evaluated again after the new hash-bound maker evidence is saved.
        profile['browser_hidden'] = row['mode'] != 'publish_reference'
        write(path, profile)
        paths.add(path)
        for view in row['views']:
            entry = next(v for v in profile['cad_don'] if v['id_hinh_goc'] == view['id'])
            metadata = (path.parent / entry['duong_dan']).with_name('thong_tin_cad_chen.json')
            info = read(metadata)
            info.update(huong_nhin=entry['huong_nhin'], bo_tri_trong_tu=entry['bo_tri_trong_tu'],
                nhan_dien_mat=entry['nhan_dien_mat'], asset_role=entry['asset_role'])
            write(metadata, info)
        outcomes.append({'n': row['n'], 'profile': row['profile'], 'id': cid,
            'source_name': row['source_name'], 'display': row['display'], 'category': row['category'],
            'decision': row['mode'], 'brand': row['brand'], 'candidate': row['brand_candidate_only'],
            'note': row['note'], 'documents': row['documents'], 'new_views': len(row['views'])})
    write(evidence_path, maker_evidence)
    write(overlay_path, overlay)
    records = []
    for row, result in zip(data['items'], outcomes):
        path = CAT / row['profile']
        profile = read(path)
        allowed = row['mode'] == 'publish_reference' and public_profile_allowed(profile, path, CAT)
        result['publication_allowed'] = allowed
        if not allowed:
            profile['browser_hidden'] = True
        else:
            profile.pop('browser_hidden', None)
        write(path, profile)
        if not allowed:
            continue
        views = []
        for entry in profile['cad_don']:
            asset = path.parent / entry['duong_dan']
            views.append({'id': entry['id_hinh_goc'], 'face': entry.get('huong_nhin'),
                'dxf': {'path': 'catalogtb/' + asset.relative_to(CAT).as_posix(), 'exists': asset.is_file()},
                'preview': {'path': 'catalogtb/' + asset.with_name('xem_truoc.svg').relative_to(CAT).as_posix(), 'exists': True}})
        preferred_id = (profile.get('cad_chen_tu') or {}).get('id_hinh_goc')
        reviewed_ids = {v['id'] for v in row['views']}
        preview_default = next(v for v in views if v['id'] in reviewed_ids)
        primary = next((v for v in views if v['id'] == preferred_id), preview_default)
        records.append({'catalog_id': result['id'], 'record_type': 'source_cad_device_or_assembly',
            'display_name': row['display'], 'model': row['model'], 'model_scope': row['model_scope'],
            'brand': row['brand'], 'brand_verified': bool(row['brand'] and not row['brand_candidate_only']),
            'brand_kind': 'generic' if row['generic_identity'] else 'manufacturer_candidate' if row['brand_candidate_only'] else 'manufacturer',
            'category': row['category'], 'description': profile['cong_dung'],
            'specifications': profile.get('thong_so', {}), 'price': None,
            'cad': {'status': 'source_cad_identity_reviewed', 'views': views,
                'default_view_id': primary['id'], 'preview': primary['preview'], 'dxf': primary['dxf']},
            'auto_select': False, 'ordering_code_verified': False,
            'evidence': profile['source_identity_review_20261118']})
    with sqlite3.connect(CAT / '_agent_index/equipment_catalog.sqlite') as db:
        for record in records:
            cid = record['catalog_id']
            exists = db.execute('SELECT record_json FROM equipment WHERE catalog_id=?', (cid,)).fetchone()
            if exists:
                previous = json.loads(exists[0])
                # Preserve prices and unrelated configuration; refresh the reviewed source identity/views.
                record = {**previous, **record, 'price': previous.get('price')}
                db.execute('UPDATE equipment SET brand=?,category=?,model=?,display_name=?,cad_status=?,record_json=? WHERE catalog_id=?',
                    (record['brand'], record['category'], record['model'], record['display_name'],
                     record['cad']['status'], json.dumps(record, ensure_ascii=False), cid))
            else:
                db.execute('INSERT INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',
                    (cid, record['brand'], record['category'], record['model'], record['display_name'],
                     record['record_type'], None, record['cad']['status'], json.dumps(record, ensure_ascii=False)))
            db.execute('DELETE FROM equipment_fts WHERE catalog_id=?', (cid,))
            db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',
                (cid, record['brand'] or '', record['category'], record['model'],
                 record['display_name'], record['description']))
    refresh_discovery(paths)
    from app.services.catalogtb_browser import _build_browser_data
    snapshot = _build_browser_data()
    write(CAT / '_agent_index/browser_display_v6.json', snapshot)
    from scripts.supplement_chint_native2d import sync_agent_export
    sync_agent_export({r['catalog_id'] for r in records})
    visible = {r['id'] for r in snapshot['items']}
    for result in outcomes:
        result['visible_in_browser'] = result['id'] in visible
    summary = {'reviewed_profiles': len(outcomes),
        'newly_visible_profiles': sum(o['visible_in_browser'] for o in outcomes),
        'publication_allowed': sum(o['publication_allowed'] for o in outcomes),
        'decisions': dict(Counter(o['decision'] for o in outcomes)),
        'remaining_not_visible': sum(not o['visible_in_browser'] for o in outcomes),
        'geometry_modified': False, 'electrical_configuration_approved': False}
    report = {'reviewed_on': data['reviewed_on'], 'summary': summary, 'items': outcomes}
    write(FOLDER / 'review_157_report.json', report)
    shutil.copy2(REVIEW, FOLDER / 'review_157_evidence.json')
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

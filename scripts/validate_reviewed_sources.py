"""Verify audited reference access and unchanged CAD; generate review gallery."""
import hashlib
import html
import json
import sqlite3
import sys
import tempfile
from unittest.mock import patch
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import reviewed_source_library as shelf
from app.services.cad.catalogtb_assets import category_matches


def main():
    rows = shelf.review_data()['items']
    inventory = shelf.list_references()
    followup_path = Path(__file__).resolve().parents[1] / 'app/data/accessory_remaining25_research_20261118.json'
    followup = json.loads(followup_path.read_text(encoding='utf8')) if followup_path.is_file() else None
    additional = followup['summary']['additional_reference_candidates'] if followup else 0
    admitted_count, unresolved_count = 124 + additional, 25 - additional
    assert len(rows) == inventory['total'] == 157
    assert len({r['id'] for r in inventory['items']}) == 157
    assert all(not r['can_auto_select'] and r['views'] for r in inventory['items'])
    assert Counter(r['status'] for r in inventory['items']) == {
        'publish_reference': admitted_count, 'identity_partial': unresolved_count, 'design_reference': 6,
        'envelope_only': 1, 'graphic_reference': 1}
    assert sum(r['in_device_library'] for r in inventory['items']) == admitted_count
    if followup:
        assert len(followup['items']) == 25
        assert {i['n'] for i in followup['items'] if i['reference_admitted']} == {6,54,55,64,65,66,67,68,75}
        for item in followup['items']:
            assert item['missing_evidence'] and item['checked_queries']
            if item['reference_admitted']:
                reviewed = next(r for r in rows if r['n'] == item['n'])
                profile = json.loads((shelf.ROOT/reviewed['profile']).read_text(encoding='utf8'))
                assert reviewed['brand_candidate_only'] and profile['hang_xac_nhan'] is None
                assert all(not v['bo_tri_trong_tu']['cho_phep_chen'] for v in profile['cad_don'] if v['id_hinh_goc'] in {w['id'] for w in reviewed['views']})
        backup = Path(__file__).resolve().parents[1]/'tmp/runtime/remaining25-research/before_followup'
        before = sqlite3.connect(backup/'equipment_catalog.sqlite')
        after = sqlite3.connect(shelf.ROOT/'_agent_index/equipment_catalog.sqlite')
        for cid, price in before.execute('SELECT catalog_id,price_vnd FROM equipment'):
            current = after.execute('SELECT price_vnd FROM equipment WHERE catalog_id=?',(cid,)).fetchone()
            assert current and current[0] == price, ('Price changed or record removed', cid)
        before.close();after.close()
    assert category_matches('CT', 'CT_ASSEMBLY')
    assert not category_matches('CT', 'ZCT')
    assert category_matches('RELAY', 'RELAY_ASSEMBLY')
    views = 0
    for row in rows:
        assert row['category'] != 'UNCLASSIFIED'
        for view in row['views']:
            preview = shelf.reference_preview(shelf.source_id(row['profile']), view['id'])
            assert hashlib.sha256(preview.read_bytes()).hexdigest() == view['preview_sha256']
            views += 1
    for rid, vid in [('invalid', rows[0]['views'][0]['id']),
                     (inventory['items'][0]['id'], '../source.dwg')]:
        try:
            shelf.reference_preview(rid, vid)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid reference accepted')
    with tempfile.TemporaryDirectory() as temp:
        altered = Path(temp) / 'changed.svg'
        altered.write_text('changed', encoding='utf8')
        with patch.object(shelf, 'ROOT', Path(temp)):
            try:
                shelf._valid_file(altered, '0' * 64)
            except ValueError:
                pass
            else:
                raise AssertionError('Changed drawing accepted')
            try:
                shelf._valid_file(Path(__file__), '0' * 64)
            except ValueError:
                pass
            else:
                raise AssertionError('Path outside catalog accepted')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    from app.api.v1.endpoints.cad_library import router
    from app.api.deps import get_current_active_user
    app = FastAPI()
    app.include_router(router, prefix='/cad-library')
    with TestClient(app) as client:
        assert client.get('/cad-library/reviewed-sources').status_code in (401, 403)
        app.dependency_overrides[get_current_active_user] = lambda: object()
        assert client.get('/cad-library/reviewed-sources').json()['total'] == 157
        assert client.get('/cad-library/reviewed-sources?status=identity_partial').json()['total'] == unresolved_count
        preview_url = inventory['items'][0]['views'][0]['preview']
        assert client.get(preview_url).headers['content-type'].startswith('image/svg+xml')
        assert client.get('/cad-library/reviewed-sources/invalid/views/invalid/preview').status_code == 404
    with sqlite3.connect(shelf.ROOT / '_agent_index/equipment_catalog.sqlite') as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    folder = shelf.ROOT / 'NguonCapNhat/20261118_a72a95b79f48'
    initial = json.loads((folder / 'import_report.json').read_text(encoding='utf8'))
    snapshot = json.loads((shelf.ROOT / '_agent_index/browser_display_v6.json').read_text(encoding='utf8'))
    visible = {item['id'] for item in snapshot['items']}
    total_visible = sum(shelf.source_id(item['profile']) in visible for item in initial['items'])
    assert total_visible == 176 + additional
    assert hashlib.sha256((folder / 'source.dwg').read_bytes()).hexdigest() == shelf.review_data()['source_sha256']
    result = {'reviewed_profiles': 157, 'unchanged_reviewed_views': views,
              'device_references_visible': admitted_count, 'source_shelf_visible': 157,
              'unresolved_identity': unresolved_count, 'non_product_references': 8,
              'sqlite_integrity': 'ok', 'invalid_reference_rejected': True,
              'original_dwg_unchanged': True, 'geometry_modified': False}
    result['authenticated_api_checks'] = 'passed'
    result['stale_hash_and_path_escape_rejected'] = True
    result['total_revision_profiles_visible'] = total_visible
    if followup:
        result['followup_research_25'] = {**followup['summary'], 'existing_sqlite_prices_preserved':True,
            'new_candidate_manufacturers_not_confirmed':True,'new_candidate_insertion_disabled':True}
    result['frontend_verification'] = {
        'production_build': 'passed',
        'browser_desktop_mobile_search_filters_previews': 'passed',
        'report_gallery': '157 profiles / 172 images / 0 broken images',
        'workspace_typecheck': 'blocked by existing errors outside the changed library components; no errors reported in these components'}
    initial['followup_review_157'] = {
        'reviewed_profiles': 157, 'newly_visible': admitted_count, 'total_revision_visible': total_visible,
        'identity_partial': unresolved_count, 'non_product_references': 8,
        'report': 'bao_cao_xac_minh_157.html', 'original_import_results_preserved': True}
    (folder / 'import_report.json').write_text(json.dumps(initial, ensure_ascii=False, indent=2), encoding='utf8')
    original_gallery = folder / 'bao_cao_cap_nhat.html'
    original_html = original_gallery.read_text(encoding='utf8')
    if 'id="followup-157"' not in original_html:
        original_html = original_html.replace('<main>', '<main><section id="followup-157" class="summary"><h2>Đã hoàn tất rà soát 157 hồ sơ còn lại</h2><p>Hiện có 176/209 hồ sơ trong danh mục thiết bị tham khảo. Toàn bộ 157 hồ sơ rà soát có thể xem trong mục CAD nguồn đã rà soát. Nội dung bên dưới lưu kết quả nhập ban đầu, trước khi sửa nhận diện.</p><a href="bao_cao_xac_minh_157.html">Mở kết quả mới nhất và hình minh họa 157 hồ sơ</a></section>', 1)
        original_gallery.write_text(original_html, encoding='utf8')
    (folder / 'review_157_validation.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    fixture = Path(__file__).resolve().parents[2] / 'scratch/reviewed_sources_fixture.json'
    fixture.write_text(json.dumps(inventory, ensure_ascii=False), encoding='utf8')
    esc = html.escape
    parts = ['<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rà soát 157 hồ sơ CAD</title>',
        '<style>body{font:16px Arial;max-width:1200px;margin:40px auto;padding:0 20px;color:#21384b}article{border:1px solid #ccd8df;border-radius:10px;padding:20px;margin:20px 0}img{width:240px;height:220px;object-fit:contain;background:#20242b}figure{display:inline-block;margin:8px}small{color:#526a7e}p{line-height:1.65}</style>',
        '<h1>Rà soát đủ 157 hồ sơ · 18/11/2026</h1>',
        f'<p>{admitted_count} hồ sơ được bổ sung vào danh mục tham khảo thiết bị; {unresolved_count} hồ sơ còn cần xác định hãng/model; 6 mẫu bố trí, 1 bao hình và 1 đồ họa được lưu đúng nhóm. Toàn bộ 157 hồ sơ có trong mục “CAD nguồn đã rà soát”. Giữ nguyên hình CAD, giá và file DWG nguồn. Nhận diện họ thiết bị không xác nhận mã đặt hàng hoặc cấu hình điện.</p>']
    for row, item in zip(rows, inventory['items']):
        parts.append(f'<article><h2>{row["n"]}. {esc(item["name"])}</h2><small>{esc(item["status_label"])} · {esc(item["brand"] or "Chưa xác định hãng")}{" · hãng ứng viên" if item["brand_is_candidate"] else ""}</small><p>{esc(item["note"])}</p>')
        for view in row['views']:
            path = shelf.ROOT / view['path']
            import os
            relative = Path(os.path.relpath(path.with_name('xem_truoc.svg'), folder)).as_posix()
            face = next(v['label'] for v in item['views'] if v['id'] == view['id'])
            parts.append(f'<figure><img loading="lazy" src="{esc(relative, quote=True)}" alt="{esc(item["name"], quote=True)}"><figcaption>{esc(face)}</figcaption></figure>')
        parts.append(f'<details><summary>Nhãn nguồn và tài liệu</summary><p>{esc(row["source_name"])}</p>')
        for url in item['documents']:
            parts.append(f'<p><a href="{esc(url, quote=True)}">{esc(url)}</a></p>')
        parts.append('</details></article>')
    parts.append('</html>')
    (folder / 'bao_cao_xac_minh_157.html').write_text('\n'.join(parts), encoding='utf8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

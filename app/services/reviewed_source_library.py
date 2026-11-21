"""Audited CAD references, including non-products and unresolved manufacturer labels.

This read-only shelf is independent of procurement admission and automatic CAD
selection. Only drawings bound to the individual review can be previewed here.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / 'data/CatalogTB'
REVIEW = Path(__file__).resolve().parents[1] / 'data/accessory_revision_review_20261118.json'


@lru_cache(maxsize=2)
def _review(path, stamp):
    return json.loads(Path(path).read_text(encoding='utf8'))


def review_data():
    if not REVIEW.is_file():
        return {'items': []}
    stat = REVIEW.stat()
    return _review(str(REVIEW), (stat.st_mtime_ns, stat.st_size))


@lru_cache(maxsize=512)
def _hash(path, stamp):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _valid_file(path, expected):
    path = path.resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError('Không tìm thấy hình nguồn hợp lệ.')
    stat = path.stat()
    if _hash(str(path), (stat.st_mtime_ns, stat.st_size)) != expected:
        raise ValueError('Hình nguồn đã thay đổi; cần rà soát lại trước khi xem.')
    return path


def source_id(relative):
    return 'TB-' + hashlib.sha1(relative.encode()).hexdigest()[:16]


def reference_preview(reference_id, view_id):
    row = next((r for r in review_data()['items'] if source_id(r['profile']) == reference_id), None)
    if row is None:
        raise ValueError('Không tìm thấy hồ sơ nguồn đã rà soát.')
    view = next((v for v in row['views'] if v['id'] == view_id), None)
    if view is None:
        raise ValueError('Không tìm thấy mặt CAD trong hồ sơ đã rà soát.')
    drawing = _valid_file(ROOT / view['path'], view['dxf_sha256'])
    return _valid_file(drawing.with_name('xem_truoc.svg'), view['preview_sha256'])


def list_references(query='', status=''):
    from .catalogtb_browser import catalog_query_matches
    items = []
    statuses = {'publish_reference': 'Sản phẩm tham khảo', 'identity_partial': 'Cần xác định hãng/model',
        'design_reference': 'Mẫu bố trí', 'envelope_only': 'Bao hình tham khảo',
        'graphic_reference': 'Đồ họa chi tiết'}
    for row in review_data()['items']:
        if status and row['mode'] != status:
            continue
        if query and not catalog_query_matches(query, ' '.join([
            row['display'], row['source_name'], row['category'], row['brand'] or '', row['model']])):
            continue
        identifier = source_id(row['profile'])
        profile_path = (ROOT / row['profile']).resolve()
        if not profile_path.is_relative_to(ROOT.resolve()) or not profile_path.is_file():
            continue
        profile = json.loads(profile_path.read_text(encoding='utf8'))
        current = {v['id_hinh_goc']: v for v in profile.get('cad_don', [])}
        views = []
        for view in row['views']:
            entry = current.get(view['id'])
            if not entry:
                continue
            views.append({'id': view['id'], 'label': entry.get('huong_nhin') or view['face'],
                'preview': f'/cad-library/reviewed-sources/{identifier}/views/{view["id"]}/preview',
                'revision': view['preview_sha256'][:16], 'role': entry.get('asset_role') or 'source_reference'})
        items.append({'id': identifier, 'name': row['display'], 'source_name': row['source_name'],
            'category': profile.get('nhom') or row['category'], 'brand': profile.get('hang_xac_nhan') or row['brand'],
            'model': profile.get('ma_dong_san_pham') or row.get('model', ''),
            'specifications': profile.get('thong_so', {}),
            'brand_is_candidate': row['brand_candidate_only'],
            'status': row['mode'], 'status_label': statuses.get(row['mode'], row['mode']),
            'note': profile.get('cong_dung') or row['note'], 'documents': row['documents'], 'views': views,
            'observed_texts': row.get('observed_texts', []),
            'in_device_library': not profile.get('browser_hidden', False),
            'can_auto_select': False, 'reviewed_on': '2026-11-18'})
    return {'items': items, 'total': len(items), 'reviewed_on': '2026-11-18'}

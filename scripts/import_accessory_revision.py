"""Import a native AutoCAD-evaluated revision without replacing curated geometry.

Prepared inputs contain source.dwg/source.dxf, native_plan.json, source_blocks.json,
insertion_inventory.json, block_diff.json and native_views/<source INSERT handle>.dxf.
Native EXPLODE is necessary: copying a dynamic BLOCK definition retains invisible
evaluation entities and can lose the MLINE body. Keep those native exports as evidence.
Unknown identities and projections remain review records, never automatic selections.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.addons.drawing.config import Configuration, HatchPolicy
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Matrix44

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.services.cad.library_taxonomy import classify, explicit_brands
from app.services.catalog_publication_policy import public_profile_allowed

CAT = BACKEND / 'data/CatalogTB'
REVISION = '20261118'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.tmp')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    pending.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))
    return text.replace('đ', 'd').replace('Đ', 'D').lower()


def key(text):
    return re.sub(r'[^a-z0-9]', '', normal(text or ''))


def family(name):
    # Only full projection words are interpreted; F/S/T stay source labels.
    return re.sub(r'\s+(?:Front|Side|Top|Rear|Bottom)$', '', name, flags=re.I).strip()


def role(name):
    n = normal(name)
    if 'khuon uon dong' in n:
        return 'FABRICATION_TOOL', 'Khuôn uốn đồng', 'Phụ kiện tủ điện'
    if 'kep' in n and ('dong' in n or 'thanh cai' in n):
        return 'BUSBAR_CLAMP', 'Kẹp giữ thanh dẫn', 'Phụ kiện tủ điện'
    if 'thanh cai' in n or 'uon' in n and 'dong' in n:
        return 'COPPERBUSBAR', 'CopperBusbar', 'Đồng'
    rules = [
        ('ban le|^hl0', 'HINGE', 'Bản lề cửa tủ'),
        ('tui ho so', 'DOCUMENT_POCKET', 'Túi đựng sơ đồ'),
        ('mica|mat kinh', 'INSPECTION_WINDOW', 'Cửa sổ quan sát'),
        ('tem tu|mac nhua', 'LABEL_HOLDER', 'Giá giữ nhãn'),
        ('mang nhua|trunking', 'WIRING_DUCT', 'Máng dây'),
        ('lifting', 'LIFTING_ATTACHMENT', 'Điểm nâng tủ'),
        ('insulator', 'INSULATING_SUPPORT', 'Trụ đỡ cách điện'),
        ('phu kien treo tay mccb', 'ACCESSORY', 'Phụ kiện tay thao tác MCCB'),
        ('lo khoet', 'PANEL_CUTOUT', 'Lỗ khoét theo nguồn'),
    ]
    for pattern, code, description in rules:
        if re.search(pattern, n):
            return code, description, 'Phụ kiện tủ điện'
    group = classify(name)['group']
    codes = {'Biến dòng': 'CT', 'Đồng hồ và công tơ': 'METER', 'Ổ cắm': 'SOCKET',
             'Đèn báo': 'LIGHT', 'Nút nhấn và còi': 'PUSHBUTTON',
             'Thiết bị đóng cắt': 'CB', 'Bộ điều khiển': 'CONTROLLER',
             'Rơ le và timer': 'RELAY', 'Quạt và lọc gió': 'FAN', 'Cầu chì': 'FUSE',
             'Chống sét': 'SPD', 'Biến tần': 'VFD', 'Cầu đấu': 'TERMINAL',
             'Bộ nguồn DC': 'POWER_SUPPLY', 'Contactor': 'CONTACTOR'}
    return codes.get(group, 'UNCLASSIFIED'), group, 'Phụ kiện tủ điện'


def projection(name):
    labels = {'front': 'Mặt trước', 'side': 'Mặt bên', 'top': 'Mặt trên',
              'rear': 'Mặt sau', 'bottom': 'Mặt dưới'}
    match = re.search(r'\s+(Front|Side|Top|Rear|Bottom)$', name, re.I)
    return labels[match[1].lower()] if match else 'Chưa xác định hướng nhìn'


def refresh_discovery(paths):
    """Update affected inventory entries, preserving unrelated curated evidence."""
    manifest_path = CAT / 'ai_library_manifest.json'
    manifest = read(manifest_path)
    inventory = {r['profile']: r for r in manifest['items']}
    index_path = CAT / 'ai_device_index.json'
    index = read(index_path)
    indexed = {r['profile']: r for r in index['items']}
    html_path = CAT / 'index.html'
    html = html_path.read_text(encoding='utf8')
    match = re.search(r'(<script id="catalog-data" type="application/json">)(.*?)(</script>)', html, re.S)
    embedded = json.loads(match[2])
    from urllib.parse import unquote
    extra_profiles = [p for p in embedded['profiles'] if not p.get('json')]
    offline = {unquote(p['json']): p for p in embedded['profiles'] if p.get('json')}
    from app.services.cad.catalogtb_assets import face_code
    for path in sorted(paths):
        profile = read(path)
        relative = path.relative_to(CAT).as_posix()
        code = (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') or 'UNCLASSIFIED'
        views = []
        offline_views = []
        for v in profile['cad_don']:
            asset = path.parent / v['duong_dan']
            views.append({'id': v['id_hinh_goc'], 'face': face_code(v.get('huong_nhin')),
                'face_label': v.get('huong_nhin'), 'path': asset.relative_to(CAT).as_posix(),
                'exists': asset.is_file(),
                'placement': v.get('bo_tri_trong_tu', {})})
            if v.get('source_revision'):
                views[-1]['units'] = 4
            offline_views.append({'source_id': v['id_hinh_goc'], 'name': profile['ten_san_pham'],
                'face': v.get('huong_nhin'), 'label': v.get('nhan_hien_thi') or v.get('huong_nhin'),
                'placement': v.get('bo_tri_trong_tu', {}),
                'dxf': quote(asset.relative_to(CAT).as_posix(), safe='/'),
                'preview': quote(asset.with_name('xem_truoc.svg').relative_to(CAT).as_posix(), safe='/'),
                'json': quote(asset.with_name('thong_tin_cad_chen.json').relative_to(CAT).as_posix(), safe='/')})
        previous = inventory.get(relative, {})
        old_views = {v.get('id'): v for v in previous.get('views', [])}
        previous.update(profile=relative, sha256=digest(path), name=profile['ten_san_pham'],
            group=profile['nhom'], brand=profile.get('hang_xac_nhan'), category_code=code,
            classification_basis='profile.nhan_dien_ai',
            recognition_status='unresolved' if code == 'UNCLASSIFIED' else 'function_identified',
            exact_SKU_verified=False, aliases=profile.get('tu_khoa_tim_kiem', []),
            views=[{**old_views.get(v['id'], {}), **v} for v in views],
            source_auto_select=profile.get('auto_select', False), source_needs_review=True)
        inventory[relative] = previous
        indexed[relative] = {**indexed.get(relative, {}), 'profile': relative,
            'name': profile['ten_san_pham'], 'category': profile['nhom'],
            'brand': profile.get('hang_xac_nhan'), 'auto_select': profile.get('auto_select', False),
            'needs_review': True, 'search_aliases': profile.get('tu_khoa_tim_kiem', [])}
        if profile.get('browser_hidden'):
            offline.pop(relative, None)
            continue
        item = offline.get(relative, {})
        selected = (profile.get('cad_chen_tu') or {}).get('id_hinh_goc')
        primary = next((v for v in offline_views if v['source_id'] == selected), offline_views[0])
        item.update(json=quote(relative, safe='/'), category=profile['nhom'],
            display=profile['ten_san_pham'], name=profile['ten_kieu'],
            brand=profile.get('hang_xac_nhan'), type=profile.get('ban_chat'),
            product_code=profile.get('ma_dong_san_pham'), spec=profile.get('thong_so', {}),
            search_aliases=profile.get('tu_khoa_tim_kiem', []), single_views=offline_views,
            primary=primary)
        item.setdefault('drawings', [])
        offline[relative] = item
    manifest['items'] = list(inventory.values())
    manifest['summary'].update(profiles=len(inventory),
        declared_cad_views=sum(len(v.get('views', [])) for v in inventory.values()))
    manifest.setdefault('revisions', {})[REVISION] = {'profiles_refreshed': len(paths)}
    write(manifest_path, manifest)
    index.update(items=list(indexed.values()), count=len(indexed))
    write(index_path, index)
    embedded['profiles'] = list(offline.values()) + extra_profiles
    payload = json.dumps(embedded, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = html[:match.start(2)] + payload + html[match.end(2):]
    pending = html_path.with_suffix('.html.tmp')
    pending.write_text(html, encoding='utf8')
    pending.replace(html_path)


def retire_hidden_import_records(paths, backup):
    """Remove only this import's provisional rows, never pre-existing records."""
    with sqlite3.connect(backup / 'equipment_catalog.sqlite') as previous:
        preserved = {row[0] for row in previous.execute('SELECT catalog_id FROM equipment')}
    retired = set()
    for path in paths:
        profile = read(path)
        if not profile.get('import_revision') or not profile.get('browser_hidden'):
            continue
        cid = 'TB-' + hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
        if cid not in preserved:
            retired.add(cid)
    with sqlite3.connect(CAT / '_agent_index/equipment_catalog.sqlite') as db:
        for cid in retired:
            db.execute('DELETE FROM equipment_fts WHERE catalog_id=?', (cid,))
            db.execute('DELETE FROM equipment WHERE catalog_id=?', (cid,))
    export = CAT / '_agent_index/equipment_catalog.jsonl'
    records = [json.loads(line) for line in export.read_text(encoding='utf8').splitlines() if line.strip()]
    pending = export.with_suffix('.tmp')
    pending.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in records
                               if row['catalog_id'] not in retired), encoding='utf8')
    pending.replace(export)
    return retired


def drawing(source, row, target):
    marker = target / 'thong_tin_cad_chen.json'
    if source.is_file() and marker.is_file():
        previous = read(marker).get('provenance', {})
        if (previous.get('native_export_sha256') == digest(source)
                and (target / 'ban_ve.dxf').is_file() and (target / 'xem_truoc.svg').is_file()
                and previous.get('dxf_sha256') == digest(target / 'ban_ve.dxf')
                and previous.get('preview_sha256') == digest(target / 'xem_truoc.svg')):
            return {k: previous[k] for k in ('width_mm', 'height_mm', 'entities',
                'excluded_unsupported', 'coordinate_scale_applied', 'native_export_sha256',
                'dxf_sha256', 'preview_sha256')}
    doc = ezdxf.readfile(source)
    if doc.units != 4:
        raise ValueError('Native export is not in millimetres')
    audit = doc.audit()
    if audit.errors:
        raise ValueError('Native export has structural errors')
    visible = []
    excluded = []
    for entity in doc.modelspace():
        if entity.dxf.get('invisible', 0):
            continue
        if entity.dxftype() in {'ACAD_PROXY_ENTITY', 'ACAD_TABLE', 'OLE2FRAME'}:
            excluded.append(entity.dxftype())
            continue
        # Dimensions and text remain in nguon_hien_thi.dxf, not placement bounds.
        if entity.dxftype() in {'DIMENSION', 'TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF'}:
            continue
        visible.extend(recursive_decompose([entity]))
    output = ezdxf.new('R2018')
    output.units = 4
    importer = Importer(doc, output)
    importer.import_entities(visible)
    importer.finalize()
    point = row['insert']
    transform = Matrix44.chain(Matrix44.translate(-point[0], -point[1], -point[2]),
                               Matrix44.z_rotate(-math.radians(row['rotation'])))
    for entity in output.modelspace():
        entity.transform(transform)
    bounds = bbox.extents(output.modelspace())
    if not bounds.has_data or max(bounds.size.x, bounds.size.y) <= 0:
        raise ValueError('No usable geometry after native evaluation')
    for entity in output.modelspace():
        entity.translate(-bounds.extmin.x, -bounds.extmin.y, -bounds.extmin.z)
    if output.audit().errors:
        raise ValueError('Imported geometry has structural errors')
    target.mkdir(parents=True, exist_ok=True)
    output.saveas(target / 'ban_ve.dxf')
    shutil.copy2(source, target / 'nguon_hien_thi.dxf')
    backend = svg.SVGBackend()
    # Preserve HATCH entities in DXF; render their outlines without expensive
    # pattern tessellation that can obscure a small library thumbnail.
    Frontend(RenderContext(output), backend,
             config=Configuration(hatch_policy=HatchPolicy.SHOW_OUTLINE)).draw_layout(output.modelspace(), finalize=True)
    preview = backend.get_string(layout.Page(160, 120, layout.Units.mm, margins=layout.Margins.all(5)))
    (target / 'xem_truoc.svg').write_text(preview, encoding='utf8')
    return dict(width_mm=round(bounds.size.x, 6), height_mm=round(bounds.size.y, 6),
                entities=len(output.modelspace()), excluded_unsupported=excluded,
                coordinate_scale_applied=1, native_export_sha256=digest(source),
                dxf_sha256=digest(target / 'ban_ve.dxf'),
                preview_sha256=digest(target / 'xem_truoc.svg'))


def main(prepared):
    source_hash = digest(prepared / 'source.dwg')
    revision = CAT / 'NguonCapNhat' / f'{REVISION}_{source_hash[:12]}'
    revision.mkdir(parents=True, exist_ok=True)
    backup = prepared / 'before_import'
    backup.mkdir(exist_ok=True)
    database = CAT / '_agent_index/equipment_catalog.sqlite'
    if not (backup / 'equipment_catalog.sqlite').exists():
        with sqlite3.connect(database) as source_db, sqlite3.connect(backup / 'equipment_catalog.sqlite') as backup_db:
            source_db.backup(backup_db)
        for filename in ('browser_display_v6.json', 'equipment_catalog.jsonl', 'manifest.json'):
            shutil.copy2(CAT / '_agent_index' / filename, backup / filename)
        for filename in ('ai_library_manifest.json', 'ai_device_index.json', 'index.html'):
            shutil.copy2(CAT / filename, backup / filename)
    plan = read(prepared / 'native_plan.json')
    visual_review_path = prepared / 'copper_visual_review.json'
    visual_review = read(visual_review_path) if visual_review_path.is_file() else {}
    if visual_review.get('source_sha256') != source_hash:
        visual_review = {}
    if visual_review:
        shutil.copy2(visual_review_path, revision / visual_review_path.name)
    # Keep the new original alongside the previous original, never overwrite it.
    for filename in ('source.dwg', 'source.dxf', 'source_blocks.json', 'insertion_inventory.json',
                     'block_diff.json', 'native_plan.json', 'native_handles.tsv'):
        shutil.copy2(prepared / filename, revision / filename)
    originals = {}
    lookup = defaultdict(set)
    for path in CAT.rglob('thong_tin_thiet_bi.json'):
        profile = read(path)
        originals[path] = profile
        if profile.get('import_revision') == source_hash:
            continue
        source_metadata = profile.get('nguon_cad') or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}
        for label in (profile.get('ma_dong_san_pham'), profile.get('ten_kieu'),
                      profile.get('ten_san_pham'), source_metadata.get('block')):
            if label and len(key(label)) >= 4:
                lookup[key(family(label))].add(path)
    groups = defaultdict(list)
    for row in plan:
        groups[family(row['base'])].append(row)
    report = {'revision': source_hash, 'source_name': 'Thư viện phụ kiện mới - Copy.dwg',
              'date': '2026-11-18', 'original_preserved': True, 'items': [], 'failed_views': []}
    public_records = []
    affected = set()
    for name, rows in groups.items():
        code, nature, category = role(name)
        matches = lookup.get(key(name), set())
        existing = next(iter(matches)) if len(matches) == 1 else None
        # A source label is insufficient to merge multiple curated product records.
        folder = (existing.parent if existing else CAT / category / 'ThietBi' /
                  ('REV20261118_' + hashlib.sha1(name.encode()).hexdigest()[:16]))
        path = folder / 'thong_tin_thiet_bi.json'
        brands = explicit_brands(name)
        profile = read(path) if path.is_file() else {
            'nhom': category, 'ten_kieu': name, 'ten_san_pham': name,
            'hang_xac_nhan': brands[0] if len(brands) == 1 else None,
            'ma_dong_san_pham': name, 'ban_chat': nature,
            'nhan_dien_ai': {'loai_thiet_bi_code': code, 'tu_dong_chon_theo_vai_tro': False,
                            'fabrication_ready': False},
            'thong_so': {}, 'auto_select': False, 'needs_review': True,
            'cong_dung': 'Mẫu CAD theo nhãn thư viện nguồn; chọn cấu hình và kiểm tra lắp đặt riêng.',
            'muc_do_xac_nhan': 'CAD nguồn đã tách bằng AutoCAD; chưa xác nhận mã mua hàng và khả năng điện.',
            'cad_don': [], 'tu_khoa_tim_kiem': [name, nature], 'import_revision': source_hash,
        }
        if profile.get('import_revision') == source_hash:
            profile['nhan_dien_ai']['loai_thiet_bi_code'] = code
            profile['ban_chat'] = nature
            profile.pop('browser_hidden', None)
            profile.pop('catalog_information_type', None)
        if existing:
            saved = backup / path.relative_to(CAT)
            if not saved.exists():
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
        elif code in {'HINGE', 'DOCUMENT_POCKET', 'INSPECTION_WINDOW', 'LABEL_HOLDER',
                       'WIRING_DUCT', 'LIFTING_ATTACHMENT', 'INSULATING_SUPPORT', 'CABINET_LOCK',
                       'BUSBAR_CLAMP', 'FABRICATION_TOOL'}:
            profile['catalog_information_type'] = nature
        views = []
        for row in rows:
            source = prepared / 'native_views' / (row['handle'] + '.dxf')
            view_id = 'REV20261118-' + row['handle']
            target = folder / 'CadDon' / view_id
            try:
                evidence = drawing(source, row, target)
            except Exception as exc:
                report['failed_views'].append({'name': name, 'handle': row['handle'], 'error': str(exc)})
                continue
            face = projection(row['base'])
            decision = visual_review.get('views', {}).get(view_id, {})
            if decision.get('native_export_sha256') == evidence['native_export_sha256']:
                face = decision['face']
            else:
                decision = {}
            provenance = dict(file=(revision / 'source.dwg').relative_to(CAT).as_posix(),
                              sha256=source_hash, source_insert=row['handle'], source_block=row['base'],
                              evaluated_block=row['block'], source_scale=row['scale'],
                              source_insert_position=row['insert'], source_rotation=row['rotation'],
                              method=row.get('recovery_method') or 'native_autocad_explode_visible_state', **evidence)
            entry = {'id_hinh_goc': view_id, 'huong_nhin': face,
                     'nhan_hien_thi': row['base'] + ' · trạng thái ' + row['handle'],
                     'duong_dan': f'CadDon/{view_id}/ban_ve.dxf',
                     'asset_role': 'fabrication_template' if code == 'COPPERBUSBAR' else 'source_reference',
                     'bo_tri_trong_tu': {'cho_phep_chen': False,
                         'huong_dan': 'Tham khảo nguồn; xác nhận hướng nhìn, biến thể và mốc gá trước khi chèn.'},
                     'kiem_tra_net_cad': {'status': 'native_visible_geometry_imported',
                         'fabrication_ready': False}, 'source_revision': provenance}
            if decision:
                entry['nhan_dien_mat'] = {'method': 'source_geometry_visual_review', **decision}
                if code == 'COPPERBUSBAR':
                    entry['bo_tri_trong_tu'] = {'cho_phep_chen': True,
                        'huong_dan': 'Mẫu đồng tham khảo bố trí theo đúng mặt đã xem; không xác nhận điện hoặc gia công. Không kéo giãn hoặc tự ghép trạng thái thành một thanh.'}
                    entry['bien_the_cad'] = view_id
            profile['cad_don'] = [v for v in profile['cad_don'] if v['id_hinh_goc'] != view_id] + [entry]
            write(target / 'thong_tin_cad_chen.json', dict(id_hinh_goc=view_id, huong_nhin=face,
                  tep={'cad_dxf': 'ban_ve.dxf', 'preview': 'xem_truoc.svg'},
                  bo_tri_trong_tu=entry['bo_tri_trong_tu'], provenance=provenance,
                  kich_thuoc_hinh_mm={'ngang': evidence['width_mm'], 'cao': evidence['height_mm']}))
            views.append(entry)
        if not views:
            continue
        if not existing:
            profile['cad_chen_tu'] = {k: views[0][k] for k in ('id_hinh_goc', 'huong_nhin', 'duong_dan')}
        profile.setdefault('source_revisions', {})[source_hash] = {
            'file': (revision / 'source.dwg').relative_to(CAT).as_posix(),
            'name': name, 'date': report['date'], 'views': [v['id_hinh_goc'] for v in views]}
        if code == 'COPPERBUSBAR' and not existing:
            thickness = re.search(r'(\d+)\s*mm$', normal(name)) if 'uon' in normal(name) else None
            profile['thong_so'].update(vat_lieu='Cu theo nhãn nguồn',
                day_nhan_nguon_mm=int(thickness[1]) if thickness else None,
                tiet_dien_da_xac_nhan_mm2=None, dong_cho_phep_A=None)
            profile['tu_khoa_tim_kiem'] += ['đồng', 'thanh đồng', 'thanh cái', 'busbar', 'copper busbar', 'đồng uốn']
            profile['tu_khoa_tim_kiem'] = list(dict.fromkeys(profile['tu_khoa_tim_kiem']))
            profile['nhan_dien_ai']['cac_cad_la_bien_the_duong_di'] = True
            profile['quy_tac_ghep_mat'] = {'auto_pair': False,
                'note': 'Các trạng thái nguồn độc lập; chưa xác nhận ghép mặt hoặc số thanh vật lý.'}
        allowed = (public_profile_allowed(profile, path, CAT)
                   and (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') != 'UNCLASSIFIED')
        if not existing and not allowed:
            profile['browser_hidden'] = True
        write(path, profile)
        affected.add(path)
        cid = 'TB-' + hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
        report['items'].append({'name': name, 'profile': path.relative_to(CAT).as_posix(),
            'action': 'append_source_alternatives' if existing else 'add_profile',
            'public': allowed, 'category': code, 'views': len(views),
            'ambiguous_existing_profiles': len(matches) if len(matches) > 1 else 0})
        print(json.dumps({'family': name, 'views': len(views), 'public': allowed}, ensure_ascii=True), flush=True)
        if not allowed:
            continue
        record_views = []
        for entry in profile['cad_don']:
            root = 'catalogtb/' + path.parent.relative_to(CAT).as_posix() + '/' + str(Path(entry['duong_dan']).parent).replace('\\', '/')
            record_views.append({'id': entry['id_hinh_goc'], 'face': entry.get('huong_nhin'),
                'dxf': {'path': root + '/ban_ve.dxf', 'exists': True},
                'preview': {'path': root + '/xem_truoc.svg', 'exists': True}})
        public_records.append({'catalog_id': cid, 'record_type': 'source_cad_device_or_assembly',
            'display_name': profile['ten_san_pham'], 'model': profile.get('ma_dong_san_pham'),
            'brand': profile.get('hang_xac_nhan'), 'brand_verified': bool(profile.get('hang_xac_nhan')),
            'category': (profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code', code),
            'description': profile.get('cong_dung'), 'specifications': profile.get('thong_so', {}),
            'price': None, 'cad': {'status': 'source_cad_unverified_sku', 'views': record_views,
                'default_view_id': record_views[0]['id'], 'preview': record_views[0]['preview'],
                'dxf': record_views[0]['dxf']}, 'auto_select': False,
            'evidence': profile['source_revisions'][source_hash]})
    retire_hidden_import_records(affected, backup)
    with sqlite3.connect(CAT / '_agent_index/equipment_catalog.sqlite') as db:
        for record in public_records:
            cid = record['catalog_id']
            previous = db.execute('SELECT record_json FROM equipment WHERE catalog_id=?', (cid,)).fetchone()
            if previous:
                original = json.loads(previous[0])
                updates = {v['id']: v for v in record['cad']['views'] if v['id'].startswith('REV20261118-')}
                original['cad']['views'] = [updates.get(v['id'], v) for v in original.get('cad', {}).get('views', [])]
                old_ids = {v['id'] for v in original['cad']['views']}
                original.setdefault('cad', {}).setdefault('views', []).extend(
                    v for v in record['cad']['views'] if v['id'] not in old_ids)
                record = original
                db.execute('UPDATE equipment SET record_json=? WHERE catalog_id=?',
                           (json.dumps(record, ensure_ascii=False), cid))
            else:
                db.execute('INSERT INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',
                    (cid, record.get('brand'), record['category'], record.get('model'), record['display_name'],
                     record['record_type'], None, record['cad']['status'], json.dumps(record, ensure_ascii=False)))
            db.execute('DELETE FROM equipment_fts WHERE catalog_id=?', (cid,))
            db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)', (cid, record.get('brand') or '',
                record['category'], record.get('model') or '', record['display_name'], record['display_name']))
    # Save the reconciliation before the potentially expensive browser refresh.
    write(revision / 'import_report.json', report)
    refresh_discovery(affected)
    # The live browser rebuilds directly from source profiles. Retain existing metadata.
    from app.services.catalogtb_browser import _build_browser_data
    snapshot = _build_browser_data()
    write(CAT / '_agent_index/browser_display_v6.json', snapshot)
    from scripts.supplement_chint_native2d import sync_agent_export
    if public_records:
        sync_agent_export({r['catalog_id'] for r in public_records})
    report['summary'] = {'families_processed': len(report['items']),
        'source_views_imported': sum(r['views'] for r in report['items']),
        'public_families': sum(r['public'] for r in report['items']),
        'new_profiles': sum(r['action'] == 'add_profile' for r in report['items']),
        'existing_profiles_extended': sum(r['action'] != 'add_profile' for r in report['items']),
        'failed_views': len(report['failed_views'])}
    write(revision / 'import_report.json', report)
    print(json.dumps(report['summary'], ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prepared', type=Path)
    args = parser.parse_args()
    main(args.prepared.resolve())

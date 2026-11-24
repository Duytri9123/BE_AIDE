"""Versioned, owner-scoped design memory. Approval is never inferred from save."""
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from functools import lru_cache


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encode(value).encode('utf8')).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').casefold())
                   if not unicodedata.combining(c)).replace('đ', 'd').strip()


def manufacturer(value):
    label = normalized(value)
    return {'schneider electric': 'schneider', 'ls electric': 'ls',
            'mitsubishi electric': 'mitsubishi', 'hd hyundai electric': 'hyundai'}.get(label, label)


def requirement(row):
    """Preserve literal specifications: unknown ratings do not act as wildcards."""
    return {key: normalized(row.get(key)) for key in
            ('category', 'brand', 'part_number', 'spec', 'poles', 'in_a', 'icu_ka',
             'coil_voltage', 'electrical_function', 'mounting_face', 'price_row_id')}


def signature(row):
    return fingerprint(requirement(row))


def semantic_design(design):
    ignored = {'selectedId', 'selectedIds', 'selectedSupport', 'selectedSupportIds', 'supportActive',
               'placements_info', 'diagnostics', 'topCover'}
    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in ignored}
        return value
    return clean(design)


@contextmanager
def database(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path.parent / 'learning.sqlite3', timeout=15)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.executescript('''
          CREATE TABLE IF NOT EXISTS revisions (
            project_key TEXT NOT NULL, revision TEXT NOT NULL, owner_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(project_key,revision));
          CREATE TABLE IF NOT EXISTS heads (project_key TEXT PRIMARY KEY, revision TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY, project_key TEXT NOT NULL, base_revision TEXT NOT NULL,
            result_revision TEXT NOT NULL, actor_id INTEGER NOT NULL, created_at TEXT NOT NULL,
            changes TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY, project_key TEXT NOT NULL, revision TEXT NOT NULL,
            design_id TEXT NOT NULL, owner_id INTEGER NOT NULL, reviewer_id INTEGER NOT NULL,
            created_at TEXT NOT NULL, reason TEXT NOT NULL, scope TEXT NOT NULL,
            status TEXT NOT NULL, evidence TEXT NOT NULL,
            UNIQUE(project_key,revision,design_id,scope));
          CREATE INDEX IF NOT EXISTS review_owner ON reviews(owner_id,status);
          CREATE TABLE IF NOT EXISTS learning_usage (
            id TEXT PRIMARY KEY, owner_id INTEGER NOT NULL, project_key TEXT NOT NULL,
            created_at TEXT NOT NULL, payload TEXT NOT NULL);
        ''')
        yield connection
    finally:
        connection.close()


def key(path):
    return str(path.resolve())


def read_snapshot(path):
    if (path.parent / 'learning.sqlite3').is_file():
        with database(path) as db:
            row = db.execute('SELECT r.payload FROM revisions r JOIN heads h '
                             'ON r.project_key=h.project_key AND r.revision=h.revision '
                             'WHERE r.project_key=?', (key(path),)).fetchone()
            if row:
                return json.loads(row['payload'])
    return json.loads(path.read_text(encoding='utf8')) if path.is_file() else {'designs': [], 'revision': ''}


def save_snapshot(path, designs, revision, owner_id=0, actor_id=0):
    """Journal and head commit atomically. JSON is a backwards-compatible mirror."""
    content = encode(designs)
    if len(content.encode('utf8')) > 20_000_000:
        raise OverflowError('Dữ liệu thiết kế vượt 20 MB.')
    ids = [d.get('id') for d in designs]
    if len(set(ids)) != len(ids):
        raise ValueError('Mã tủ thiết kế bị trùng.')
    with database(path) as db:
        db.execute('BEGIN IMMEDIATE')
        head = db.execute('SELECT revision FROM heads WHERE project_key=?', (key(path),)).fetchone()
        if head:
            previous = json.loads(db.execute('SELECT payload FROM revisions WHERE project_key=? AND revision=?',
                                            (key(path), head['revision'])).fetchone()['payload'])
        else:
            previous = json.loads(path.read_text(encoding='utf8')) if path.is_file() else {'revision': '', 'designs': []}
        if revision != previous.get('revision', ''):
            raise ValueError('Thiết kế đã đổi ở cửa sổ khác. Tải lại trước khi lưu.')
        if semantic_design(previous.get('designs', [])) == semantic_design(designs):
            return {'revision': revision}
        stamp = now()
        # Retain the imported baseline too, so the first correction has a real before.
        if not head and previous.get('revision'):
            db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)',
                       (key(path), revision, owner_id, actor_id, stamp, encode(previous)))
        result = {'schema_version': 2, 'revision': uuid4().hex, 'designs': designs}
        before = {d['id']: d for d in previous.get('designs', [])}
        after = {d['id']: d for d in designs}
        changes = [{'design_id': ident, 'before': before.get(ident), 'after': after.get(ident)}
                   for ident in sorted(before.keys() | after.keys())
                   if semantic_design(before.get(ident)) != semantic_design(after.get(ident))]
        db.execute('INSERT INTO revisions VALUES(?,?,?,?,?,?)',
                   (key(path), result['revision'], owner_id, actor_id, stamp, encode(result)))
        db.execute('INSERT INTO heads VALUES(?,?) ON CONFLICT(project_key) DO UPDATE SET revision=excluded.revision',
                   (key(path), result['revision']))
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?)',
                   (uuid4().hex, key(path), revision, result['revision'], actor_id, stamp, encode(changes)))
        db.commit()
    # Reads use the committed database even if a mirror write is interrupted.
    try:
        temporary = path.with_suffix('.' + uuid4().hex + '.tmp')
        temporary.write_text(encode(result), encoding='utf8')
        temporary.replace(path)
    except OSError:
        pass
    return {'revision': result['revision']}


def profile_root():
    backend = Path(__file__).resolve().parents[3]
    deployed = backend / 'data/design_learning/device-blocks'
    if (deployed / 'cad-profiles.json').is_file():
        return deployed
    return backend.parent / 'AIDE/packages/cad-viewer-example/public/device-blocks'


def load_profiles():
    path = profile_root() / 'cad-profiles.json'
    return json.loads(path.read_text(encoding='utf8')) if path.is_file() else []


def profile_evidence(profile):
    views = {v.get('face'): v for v in profile.get('views', [])}
    if not all(face in views for face in ('front', 'side')):
        raise ValueError('Thiếu mặt trước hoặc mặt bên có nguồn.')
    artifacts = []
    for face in ('front', 'side'):
        view = views[face]
        if view.get('units') != 'mm' or not all(isinstance(view.get(k), (float, int)) and
                not isinstance(view[k], bool) and math.isfinite(view[k]) and view[k] > 0 for k in ('width', 'height')):
            raise ValueError('Kích thước hoặc đơn vị CAD chưa đủ bằng chứng.')
        ref = str(view.get('geometry_ref', ''))
        if not re.fullmatch(r'geometry/[a-f0-9]{32}\.json(?:\.gz)?', ref):
            raise ValueError('Thiếu tham chiếu hình học CAD.')
        path = profile_root() / ref
        if not path.is_file():
            raise ValueError('Tệp hình học CAD không tồn tại.')
        artifacts.append({'face': face, 'ref': ref,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'profile_id': profile['id'], 'fingerprint': fingerprint(profile), 'artifacts': artifacts}


def profile_category(profile):
    text = normalized(profile.get('name'))
    for code, pattern in (
        ('RCBO', r'\brcbo\b'), ('RCCB', r'\brccb\b'), ('ELCB', r'\belcb\b'),
        ('MCCB', r'\bmccb\b|aptomat khoi'), ('MCB', r'\bmcb\b|aptomat tep'),
        ('ACB', r'\bacb\b'), ('THERMAL_RELAY', r'thermal|nhiet'),
        ('CONTACTOR', r'contactor|khoi dong tu'), ('TIMER', r'timer|hen gio'),
        ('FUSE', r'fuse|cau chi'), ('SELECTOR', r'selector|chuyen mach'),
        ('PUSHBUTTON', r'pushbutton|button|nut nhan'), ('LIGHT', r'light|pilot|den bao'),
        ('METER', r'meter|dong ho|von ke|ampe ke'), ('TERMINAL_BLOCK', r'terminal|cau dau'),
        ('POWER_SUPPLY', r'power supply|nguon dc')):
        if re.search(pattern, text):
            return code
    return ''


@lru_cache(maxsize=64)
def _row_shard(path, stamp):
    return json.loads(Path(path).read_text(encoding='utf8'))


def bound_model(profile, row):
    """An ordering code may use family CAD only through its published explicit link."""
    ident = str(row.get('price_row_id') or '')
    if not re.fullmatch(r'[a-f0-9]{24}', ident):
        return False
    path = profile_root() / 'rows' / (ident[:2] + '.json')
    if not path.is_file():
        return False
    package = _row_shard(str(path), path.stat().st_mtime_ns).get(ident) or {}
    product = package.get('product') or {}
    if normalized(product.get('sku')) != normalized(row.get('part_number')):
        return False
    brand = manufacturer(row.get('brand'))
    if brand not in ('', 'asian', 'asia', 'all') and manufacturer(product.get('brand')) != brand:
        return False
    views = {v.get('face'): v for v in profile.get('views', [])}
    for candidate in package.get('candidates', []):
        candidate_id = str(candidate.get('id') or '')
        if candidate_id != profile['id'] and not candidate_id.startswith(profile['id'] + ':'):
            continue
        if all((candidate.get(face) or {}).get('geometry_ref') and
               (candidate.get(face) or {}).get('geometry_ref') == views.get(face, {}).get('geometry_ref')
               for face in ('front', 'side')):
            return True
    return False


def official_family_reference(profile, row):
    path = Path(__file__).resolve().parents[2] / 'data/design_learning_model_families.json'
    if not path.is_file():
        return None
    for link in json.loads(path.read_text(encoding='utf8')).get('links', []):
        if (link['profile_id'] == profile['id'] and manufacturer(link['brand']) == manufacturer(row.get('brand'))
                and normalized(link['model']) == normalized(row.get('part_number'))
                and str(link['poles']) == str(row.get('poles')).removesuffix('.0')
                and normalized(link['category']) == normalized(row.get('category'))
                and row.get('in_a') is not None and float(link['current_a']) == float(row['in_a'])):
            return link
    return None


def compatible(profile, row):
    wanted = requirement(row)
    category = wanted['category'].upper()
    aliases = {'FUSE_HOLDER': 'FUSE', 'CAU_CHI': 'FUSE', 'PILOT_LIGHT': 'LIGHT',
               'PHASE_LIGHT': 'LIGHT', 'BUTTON': 'PUSHBUTTON', 'VOLTMETER': 'METER', 'AMMETER': 'METER'}
    actual = profile_category(profile)
    if aliases.get(category, category) != actual:
        return False
    brand = wanted['brand']
    if brand not in ('', 'asian', 'asia', 'all', 'chua xac dinh hang') and manufacturer(brand) != manufacturer(profile.get('brand')):
        return False
    text = normalized(profile.get('name'))
    poles = wanted['poles']
    try:
        current = float(wanted.get('in_a') or 0)
    except (ValueError, TypeError):
        current = 0
    frames = [int(value) for match in re.findall(r'(?:abn|abs|ts|cvs|nsx|ns)\s*[- ]?(\d{2,4})(?:\s*[-/]\s*(\d{2,4}))?', text) for value in match if value]
    if actual == 'MCCB' and current > max([100] + frames):
        return False
    if actual in ('MCB','RCBO','RCCB') and current > 63:
        return False
    if poles and actual in ('MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB', 'ELCB', 'CONTACTOR', 'THERMAL_RELAY'):
        if not re.search(r'\b' + re.escape(poles.removesuffix('.0')) + r'\s*p\b', text):
            return False
    model = wanted['part_number']
    if (model and not re.search(r'(?<![a-z0-9])' + re.escape(model) + r'(?![a-z0-9])', text)
            and not bound_model(profile, row) and not official_family_reference(profile, row)):
        return False
    return True


def assembly_evidence(design):
    """Learn reviewed mechanical defaults without labeling them as exact OEM CAD."""
    import math
    state = design.get('state') or {}
    report = state.get('engineeringReport') or {}
    if report.get('policy') != 'functional-cabinet-v2':
        raise ValueError('Cần phân tích lại tủ bằng bộ quy tắc chức năng hiện tại trước khi duyệt bố trí mặc định.')
    dims = ((state.get('sourceForm') or {}).get('model') or {}).get('body_dimensions') or {}
    custom = {d['id']: d for d in state.get('customDevices', [])}
    placements = state.get('placements') or []
    if not placements or len({p['id'] for p in placements}) != len(placements):
        raise ValueError('Thiếu thiết bị hoặc ID thiết bị bị trùng.')
    if (state.get('diagnostics') or {}).get('collisions'):
        raise ValueError('Bố trí còn va chạm; chưa được học làm mẫu.')
    choices, layout, boxes = [], [], []
    for p in placements:
        d = custom.get(p.get('sourceId')) or {}
        values = [d.get(k) for k in ('width', 'height', 'depth')] + [p.get(k) for k in ('x', 'y', 'standoff')]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values) or min(values[:3]) <= 0:
            raise ValueError('Khối mặc định thiếu kích thước hữu hạn theo mm.')
        w, h, depth, x, y, z = values
        if p.get('rotation', 0) % 180:
            w, h = h, w
        if x < 0 or y < 0 or x+w > dims.get('width', 0) or y+h > dims.get('height', 0) or z < 0 or z+depth > dims.get('depth', 0):
            raise ValueError('Thiết bị vượt bao hình tủ; cần đánh giá lại.')
        owner = p.get('owner', 'mounting_plate')
        if owner not in ('mounting_plate','inner_door','outer_door'):
            raise ValueError('Mặt lắp không hợp lệ.')
        for other in boxes:
            if owner == other[0] and min(x+w, other[1]+other[3])-max(x, other[1]) > .1 and min(y+h, other[2]+other[4])-max(y, other[2]) > .1:
                raise ValueError('Thiết bị chồng nhau trên cùng mặt lắp.')
        boxes.append((owner, x, y, w, h))
        product = d.get('product') or {}
        descriptor = {'category': product.get('category'), 'poles': product.get('poles'), 'current': product.get('in_a'),
                      'function': product.get('electrical_function'), 'load': product.get('connected_load'),
                      'requested_brand': product.get('requested_brand', product.get('brand')), 'profile': d.get('catalog_profile_id'),
                      'dimensions': values[:3], 'visual': d.get('visualModel'), 'views': {k: fingerprint(d.get(k)) for k in ('front', 'side')},
                      'origin': product.get('origin'), 'assembly': product.get('assembly_components'), 'integrated': product.get('integrated_accessories')}
        choices.append({'signature': fingerprint(descriptor)})
        layout.append({k: p.get(k) for k in ('id','sourceId','x','y','owner','rotation','standoff')})
    context = {'policy': report['policy'], 'template_id': (state.get('sourceForm') or {}).get('base_template_id') or state.get('templateId'),
               'dimensions': dims, 'bom': sorted(CounterLike(c['signature'] for c in choices).items())}
    return {'design_fingerprint': fingerprint(semantic_design(design)), 'context_fingerprint': fingerprint(context), 'context': context,
            'selections': [], 'assembly_choices': choices, 'layout': layout, 'scope': 'assembly_layout',
            'claim': 'reviewed_mechanical_preferences_only_not_electrical_or_OEM_certification'}


def design_evidence(design, scope, profiles, component_ids=None):
    if scope == 'assembly_layout':
        if component_ids:
            raise ValueError('Duyệt bố trí mặc định cần toàn bộ tủ.')
        return assembly_evidence(design)
    state = design.get('state') or {}
    custom = {d['id']: d for d in state.get('customDevices', [])}
    placements = state.get('placements', [])
    if component_ids:
        ids = set(component_ids)
        if scope != 'device_selection' or len(ids) != len(component_ids) or not ids.issubset({p['id'] for p in placements}):
            raise ValueError('Phạm vi chọn thiết bị không hợp lệ; duyệt bố trí cần kiểm tra toàn bộ tủ.')
        placements = [p for p in placements if p['id'] in ids]
    if not placements:
        raise ValueError('Tủ chưa có thiết bị để học.')
    selections, layout = [], []
    for p in placements:
        device = custom.get(p.get('sourceId'), {})
        requested = device.get('takeoff_requirement')
        if not requested:
            raise ValueError('Thiếu yêu cầu bóc tách gốc của thiết bị; nhập lại từ danh sách bóc tách trước khi duyệt học.')
        profile_id = device.get('catalog_profile_id')
        profile = profiles.get(profile_id)
        if not profile or not compatible(profile, requested):
            raise ValueError('CAD chưa khớp hãng, loại, model hoặc số cực của yêu cầu nguồn.')
        if device.get('geometry_status') == 'parametric_unverified':
            raise ValueError('Bao hình tạm không được dùng làm mẫu CAD đúng.')
        evidence = profile_evidence(profile)
        views = {v['face']: v for v in profile['views']}
        if any((device.get(face) or {}).get('geometry_ref') != views[face].get('geometry_ref')
               for face in ('front', 'side')):
            raise ValueError('Mặt CAD đang dùng khác hồ sơ nguồn đã chọn.')
        expected = (views['front']['width'], views['front']['height'], views['side']['width'])
        if any(not isinstance(device.get(k), (int, float)) or abs(device[k]-v) > .5
               for k, v in zip(('width', 'height', 'depth'), expected)):
            raise ValueError('Bao hình đã khác CAD nguồn; cần kiểm tra lại trước khi duyệt học.')
        selections.append({'requirement': requirement(requested), 'signature': signature(requested),
                           'profile_id': profile_id, 'evidence': evidence})
        layout.append({k: p.get(k) for k in ('id', 'sourceId', 'x', 'y', 'owner', 'rotation', 'standoff')})
    template = state.get('sourceForm') or {}
    context = {'template_id': template.get('base_template_id') or state.get('templateId'),
               'dimensions': (template.get('model') or {}).get('dimensions'),
               'bom': sorted(CounterLike(s['signature'] for s in selections).items()),
               'geometry': sorted({s['evidence']['fingerprint'] for s in selections})}
    context['mounting_mode'] = state.get('mountingMode')
    context['requirements'] = {k: v for k, v in (state.get('projectBrief') or {}).items() if k != 'name'}
    if scope == 'layout':
        diagnostics = state.get('diagnostics') or {}
        if diagnostics.get('collisions') or diagnostics.get('outside'):
            raise ValueError('Bố trí còn lỗi va chạm hoặc vượt biên.')
        # These are server-side envelope checks, never electrical/fabrication approval.
        dims = context['dimensions'] or {}
        boxes = []
        for p in placements:
            device = custom[p['sourceId']]
            values = [p.get('x'), p.get('y'), p.get('standoff', 0), device.get('width'), device.get('height'), device.get('depth')]
            if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
                raise ValueError('Tọa độ hoặc bao hình chưa hợp lệ.')
            x, y, z, w, h, d = values
            if int(p.get('rotation', 0)) % 180:
                w, h = h, w
            face = p.get('owner') or 'mounting_plate'
            if x < 0 or y < 0 or z < 0 or min(w, h, d) <= 0 or x+w > dims.get('width', 0) or y+h > dims.get('height', 0) or z+d > dims.get('depth', 0):
                raise ValueError('Thiết bị vượt bao hình tủ; cần rà soát bố trí.')
            for ox, oy, ow, oh, other in boxes:
                if face == other and x < ox+ow-.1 and x+w > ox+.1 and y < oy+oh-.1 and y+h > oy+.1:
                    raise ValueError('Bao hình thiết bị cùng mặt đang chồng lấn.')
            boxes.append((x, y, w, h, face))
    return {'selections': selections, 'layout': layout, 'context': context,
            'design_fingerprint': fingerprint(semantic_design(design)),
            'context_fingerprint': fingerprint(context),
            'approval_limit': 'user_reviewed_cad_selection_and_nominal_layout_not_electrical_or_fabrication'}


def CounterLike(values):
    from collections import Counter
    return Counter(values)


def approve(path, owner_id, actor_id, revision, design_id, scope, reason, component_ids=None):
    if scope not in ('device_selection', 'layout', 'assembly_layout') or len(reason.strip()) < 3:
        raise ValueError('Chọn phạm vi và nhập lý do đối chiếu trước khi duyệt.')
    profiles = {p['id']: p for p in load_profiles()}
    with database(path) as db:
        db.execute('BEGIN IMMEDIATE')
        head = db.execute('SELECT revision FROM heads WHERE project_key=?', (key(path),)).fetchone()
        if not head or head['revision'] != revision:
            raise ValueError('Thiết kế đã thay đổi hoặc chưa lưu. Lưu và mở lại phần duyệt.')
        record = db.execute('SELECT payload,owner_id FROM revisions WHERE project_key=? AND revision=?', (key(path), revision)).fetchone()
        if record['owner_id'] != owner_id:
            raise ValueError('Chủ sở hữu dữ liệu không khớp.')
        design = next((d for d in json.loads(record['payload'])['designs'] if d['id'] == design_id), None)
        if not design:
            raise ValueError('Không tìm thấy tủ trong phiên bản đã lưu.')
        evidence = design_evidence(design, scope, profiles, component_ids)
        stored_scope = scope + ':' + fingerprint(sorted(component_ids))[:16] if component_ids else scope
        existing = db.execute('SELECT id,status FROM reviews WHERE project_key=? AND revision=? AND design_id=? AND scope=?',
                              (key(path), revision, design_id, stored_scope)).fetchone()
        if existing:
            # Repeat requests are idempotent; a revoked review is never silently restored.
            return {'review_id': existing['id'], 'status': existing['status']}
        review_id = uuid4().hex
        db.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (review_id, key(path), revision, design_id, owner_id, actor_id, now(), reason, stored_scope, 'approved', encode(evidence)))
        db.commit()
        return {'review_id': review_id, 'status': 'approved'}


def active_cases(db, owner_id, allowed_projects):
    # Authorization is supplied from live Project rows, including soft-delete state.
    allowed = {key(p) for p in allowed_projects}
    rows = db.execute('SELECT * FROM reviews WHERE owner_id=? AND status=? ORDER BY created_at DESC', (owner_id, 'approved')).fetchall()
    profiles = {p['id']: p for p in load_profiles()}
    result, seen = [], set()
    for row in rows:
        if row['project_key'] not in allowed:
            continue
        head = db.execute('SELECT revision FROM heads WHERE project_key=?', (row['project_key'],)).fetchone()
        if not head:
            continue
        data = json.loads(row['evidence'])
        current = json.loads(db.execute('SELECT payload FROM revisions WHERE project_key=? AND revision=?',
                                       (row['project_key'], head['revision'])).fetchone()['payload'])
        design = next((d for d in current['designs'] if d['id'] == row['design_id']), None)
        if not design or fingerprint(semantic_design(design)) != data.get('design_fingerprint'):
            continue
        valid = True
        for selection in data['selections']:
            profile = profiles.get(selection['profile_id'])
            try:
                valid = valid and profile is not None and compatible(profile, selection['requirement']) and profile_evidence(profile) == selection['evidence']
            except ValueError:
                valid = False
        group = (row['project_key'], row['design_id'], row['scope'], data['context_fingerprint'])
        if not valid or group in seen:
            continue
        seen.add(group)
        result.append({**dict(row), 'evidence': data})
    return result


def recommendations(path, owner_id, devices, allowed_projects):
    profiles = load_profiles()
    with database(path) as db:
        cases = active_cases(db, owner_id, allowed_projects)
    results = []
    for row in devices:
        sig = signature(row)
        votes, sources, seen_votes = {}, {}, set()
        for case in cases:
            # Multiple physical copies in the same approved design only cast one vote.
            choices = {s['profile_id'] for s in case['evidence']['selections'] if s['signature'] == sig}
            for profile_id in choices:
                vote_key = (case['evidence']['context_fingerprint'], profile_id)
                if vote_key in seen_votes:
                    continue
                seen_votes.add(vote_key)
                votes[profile_id] = votes.get(profile_id, 0) + 1
                sources.setdefault(profile_id, []).append(case['id'])
        pool = []
        for profile in profiles:
            if not compatible(profile, row):
                continue
            try:
                evidence = profile_evidence(profile)
            except ValueError:
                continue
            pool.append({'profile_id': profile['id'], 'name': profile['name'], 'brand': profile.get('brand'),
                         'approved_cases': votes.get(profile['id'], 0), 'review_ids': sources.get(profile['id'], []),
                         'family_reference': official_family_reference(profile, row),
                         'exact_variant_geometry_verified': False,
                         'envelope_volume': next(v['width']*v['height'] for v in profile['views'] if v.get('face') == 'front') * next(v['width'] for v in profile['views'] if v.get('face') == 'side'),
                         'evidence_fingerprint': evidence['fingerprint']})
        pool.sort(key=lambda p: (-p['approved_cases'], p['envelope_volume'], p['profile_id']))
        # A family match remains a proposal; the source's electrical requirements are unchanged.
        results.append({'signature': sig, 'candidates': pool[:10],
                        'status': 'learned' if pool and pool[0]['approved_cases'] else 'catalog_proposal' if pool else 'needs_evidence',
                        'electrical_verification_required': True,
                        'reason': 'Ưu tiên lựa chọn đã được bạn duyệt trong cùng yêu cầu.' if pool and pool[0]['approved_cases']
                                  else 'Khớp loại, hãng, model nếu có và số cực; cần đối chiếu thông số điện đúng biến thể.'})
    return {'items': results, 'active_cases': len(cases), 'memory_version': fingerprint(sorted(c['id'] for c in cases))}


def overview(path, owner_id, allowed_projects):
    with database(path) as db:
        cases = active_cases(db, owner_id, allowed_projects)
        history = db.execute('SELECT id,base_revision,result_revision,actor_id,created_at FROM events '
                             'WHERE project_key=? ORDER BY created_at DESC LIMIT 30', (key(path),)).fetchall()
        reviews = db.execute('SELECT id,revision,design_id,scope,status,reason,created_at FROM reviews '
                             'WHERE project_key=? AND owner_id=? ORDER BY created_at DESC LIMIT 30', (key(path), owner_id)).fetchall()
    active_ids = {c['id'] for c in cases}
    return {'history': [dict(h) for h in history],
            'reviews': [{**dict(r), 'active': r['id'] in active_ids} for r in reviews],
            'active_cases': len(cases), 'memory_version': fingerprint(sorted(active_ids)),
            'accuracy': None, 'accuracy_status': 'Chưa có bộ kiểm tra độc lập; số mẫu đã duyệt không phải độ chính xác.'}


def layout_suggestion(path, owner_id, revision, design_id, allowed_projects):
    current = read_snapshot(path)
    if current.get('revision') != revision:
        raise ValueError('Thiết kế đã thay đổi. Lưu lại trước khi tìm mẫu bố trí.')
    design = next((d for d in current['designs'] if d['id'] == design_id), None)
    if not design:
        raise ValueError('Không tìm thấy tủ đang chọn.')
    with database(path) as db:
        cases = active_cases(db, owner_id, allowed_projects)
    try:
        assembled = assembly_evidence(design)
    except ValueError:
        assembled = None
    if assembled:
        for case in cases:
            data = case['evidence']
            if case['scope'] != 'assembly_layout' or data['context_fingerprint'] != assembled['context_fingerprint']:
                continue
            if case['project_key'] == key(path) and case['design_id'] == design_id:
                continue
            source = {}
            for choice, placement in zip(data['assembly_choices'], data['layout']):
                source.setdefault(choice['signature'], []).append(placement)
            plan = []
            for choice, placement in zip(assembled['assembly_choices'], assembled['layout']):
                target = source[choice['signature']].pop(0)
                plan.append({**target, 'id': placement['id'], 'sourceId': placement['sourceId']})
            return {'status': 'suggested', 'review_id': case['id'], 'revision': revision,
                    'placements': plan, 'requires_revalidation': True, 'scope': 'assembly_layout',
                    'claim': 'mechanical_preferences_only'}
    try:
        evidence = design_evidence(design, 'device_selection', {p['id']: p for p in load_profiles()})
    except ValueError:
        return {'status': 'no_compatible_case', 'placements': [], 'message': 'Chưa có bố trí mặc định đã duyệt phù hợp; CAD đúng mã vẫn cần đối chiếu riêng.'}
    for case in cases:
        data = case['evidence']
        if case['scope'] != 'layout' or data['context_fingerprint'] != evidence['context_fingerprint']:
            continue
        if case['project_key'] == key(path) and case['design_id'] == design_id:
            continue
        source = {}
        for choice, placement in zip(data['selections'], data['layout']):
            source.setdefault(choice['signature'], []).append(placement)
        plan = []
        for choice, placement in zip(evidence['selections'], evidence['layout']):
            target = source[choice['signature']].pop(0)
            plan.append({**target, 'id': placement['id'], 'sourceId': placement['sourceId']})
        return {'status': 'suggested', 'review_id': case['id'], 'revision': revision,
                'placements': plan, 'requires_revalidation': True}
    return {'status': 'no_compatible_case', 'placements': [],
            'message': 'Chưa có mẫu bố trí đã duyệt cùng vỏ, kích thước, yêu cầu và bộ thiết bị.'}


def revoke(path, owner_id, review_id):
    with database(path) as db:
        with db:
            cursor = db.execute('UPDATE reviews SET status=? WHERE id=? AND project_key=? AND owner_id=?',
                                ('revoked', review_id, key(path), owner_id))
            if not cursor.rowcount:
                raise ValueError('Không tìm thấy quyết định duyệt của dự án.')
    return {'status': 'revoked'}

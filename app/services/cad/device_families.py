"""Device identity is independent of its source drawing cell and view count."""
import re
from collections import defaultdict
from app.services.cad.library_taxonomy import normalize

FACE_LABELS = {'front': 'Mặt trước', 'side': 'Mặt bên', 'top': 'Mặt trên',
               'rear': 'Mặt sau', 'section': 'Mặt cắt', 'isometric': 'Hình trục đo', 'unknown': 'Hình nguồn'}


def identity(item):
    block = item.get('source_block') or item['name']
    key = normalize(block).strip()
    brand = item.get('brand', 'Chưa xác định hãng')
    recognition = item.get('recognition') or {}
    if recognition.get('family'):
        return recognition['family'], recognition['name'], brand, recognition.get('face') or 'unknown'
    face = recognition.get('face') or 'unknown'
    form = re.fullmatch(r'tu (\d+)kvar(?:\s*-\s*(\d+))?', key)
    if form:
        return f'capacitor:{form[1]}', recognition.get('name') or f'Tụ bù · {block} (tên nguồn)', brand, 'unknown'
    for pattern, value in [(r'front|mat truoc|chieu dung', 'front'),
                           (r'side|mat ben|chieu hong', 'side'),
                           (r'top|mat tren|chieu bang|chieu tren', 'top'), (r'rear|mat sau', 'rear')]:
        if re.search(pattern, key):
            face = value
            break
    # This suffix convention is confirmed by source position and the CML source table.
    match = re.fullmatch(r'(cml\d+a|kde\s*\d+a)-([123])', key)
    if match:
        model, number = match.groups()
        face = {'1': 'front', '2': 'side', '3': 'top'}[number]
        rating = re.search(r'\d+', model).group()
        # CML/KDE are source series labels; they do not prove a manufacturer.
        brand = item.get('brand', 'Chưa xác định hãng')
        return f'ct:{model.replace(" ", "")}', f'Biến dòng {model.upper()} · {rating}/5 A', brand, face
    match = re.fullmatch(r'den (do|vang|xanh)', key)
    if match:
        color = {'do': 'đỏ', 'vang': 'vàng', 'xanh': 'xanh dương'}[match[1]]
        return f'pilot:{match[1]}', f'Đèn báo pha màu {color}', 'Dùng chung nhiều hãng', 'front'
    names = {'warning light': 'Đèn cảnh báo', 'von-to': 'Vôn kế loại lớn',
             'von-nho': 'Vôn kế loại nhỏ', 'am-nho': 'Ampe kế loại nhỏ', 'am-to': 'Ampe kế loại lớn'}
    if key in names:
        return key, names[key], brand, face
    family = re.sub(r'[- _]*(front|side|top|rear|mat truoc|mat ben|mat tren|chieu hong|chieu dung|chieu bang|chieu tren)\b', '', key).strip()
    # Unknown orientation remains unknown; a rectangular silhouette is not evidence.
    if face != 'unknown':
        return f'{brand}:{family}', recognition.get('name') or family.upper(), brand, face
    # Identical named geometry reused by another source is one device, not a new SKU.
    digest = item.get('geometry_fingerprint')
    return f'geometry:{brand}:{key}:{digest}' if digest else f'asset:{item["id"]}', recognition.get('name') or f"{item.get('group', 'Thiết bị')} · {item['name']}", brand, face


def usable_component(item):
    from app.services.cad.library_taxonomy import classify
    classification = classify(item['name'], item.get('category', ''))
    return (not item.get('is_collection') and item.get('library') != 'source_cells'
            and item.get('kind', classification['kind']) != 'unclassified'
            and not re.search(r'khungten|khung chuan|khung kt', normalize(item['name'])))


def build_families(items):
    groups = defaultdict(list)
    for item in items:
        if not usable_component(item):
            continue
        key, name, brand, face = identity(item)
        if item.get('library') == 'formtu' and re.search(r'khungten|khung chuan|khung kt', normalize(item['name'])):
            continue
        groups[key].append({**item, 'face': face, 'device_name': name, 'device_brand': brand})
    result = []
    for key, members in groups.items():
        # Prefer explicit named original blocks to copies extracted from a table.
        members.sort(key=lambda m: (m.get('library') == 'source_components', m['id']))
        views = []
        seen = set()
        for member in members:
            token = member['face'] if member['face'] != 'unknown' else (member.get('geometry_fingerprint') or member.get('geometry_sha256', member['id']))
            recognition = member.get('recognition') or {}
            token = (token, recognition.get('view_variant'))
            if token in seen: continue
            seen.add(token)
            views.append({'asset_id': member['id'], 'face': member['face'], 'title': recognition.get('view_title') or FACE_LABELS[member['face']]})
        views.sort(key=lambda v: list(FACE_LABELS).index(v['face']))
        first = members[0]
        result.append(dict(id=key, name=first['device_name'], brand=first['device_brand'],
                           kind=first['kind'], group=first['group'], views=views,
                           asset_ids=[m['id'] for m in members], thumbnail_id=views[0]['asset_id'],
                           sources=sorted({m['source_file'] for m in members}),
                           recognition={**(first.get('recognition') or {}), 'texts':list(dict.fromkeys(t for m in members for t in (m.get('recognition') or {}).get('texts', [])))},
                           original_count=len(members)))
    return result

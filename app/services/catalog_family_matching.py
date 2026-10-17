"""Match information rows to CAD families without requiring an ordering code.

Prices are deliberately excluded. A family match is not an approval of the
electrical rating or the physical interchangeability of a particular SKU.
"""
import re
from app.services.ai.manufacturer_registry import canonical_brand


def compact(value):
    return re.sub(r'[^A-Z0-9]', '', str(value or '').upper())


def category_key(value):
    key = re.sub(r'[\s_-]', '', str(value or '')).upper()
    return {'VFD':'INVERTER','SELECTOR':'SELECTORSWITCH','INDICATOR':'LIGHT',
            'PILOTLAMP':'LIGHT','PILOTLIGHT':'LIGHT','FUSEASSEMBLY':'FUSEHOLDER',
            'RCD':'RCCB','AUXCONTACT':'AUXCONTACT','TERMINAL':'TERMINALBLOCK',
            'POWERSUPPLY':'POWERSUPPLY','PHASERELAY':'PHASERELAY'}.get(key,key)


def poles(value):
    text = str(value or '').upper().strip()
    if re.fullmatch('[1-4]', text):
        return text + 'P'
    match = re.search(r'(?<![0-9])[1-4]\s*P(?:\s*\+\s*N)?(?![A-Z])', text)
    return re.sub(r'\s+', '', match[0]) if match else None


def row_poles(row):
    spec = row.get('specifications') or {}
    return poles(' '.join(str(spec.get(k) or '') for k in ('Số cực', 'Poles', 'Cực', 'so_cuc'))) or poles(row.get('name') or row.get('item_name') or row.get('sku'))


def source_identity(raw, display):
    # Do not search aliases: previous enrichment put unrelated catalog SKUs there.
    values = [raw.get(k) for k in ('ma_dong_san_pham', 'ten_kieu', 'ten_san_pham')]
    values.append(display.get('display'))
    values += (raw.get('nhan_dien_ai') or {}).get('cac_ma_dong_san_pham') or []
    source = raw.get('nguon_cad') or []
    if isinstance(source, list):
        values += [r.get('effective_block') or r.get('block') for r in source if isinstance(r, dict)]
    elif isinstance(source, dict):
        values += [source.get('block'),source.get('effective_block')]
    spec = raw.get('thong_so') or {}
    values += [spec.get(k) for k in ('nhan_block_nguon','nhan_tren_hinh','Mã/dòng trên nguồn')]
    for variant in (raw.get('source_catalog_review') or {}).get('shared_source_variants') or []:
        values += variant.get('models') or []
    # Only reviewed manufacturer evidence supplies an additional model here.
    reviewed = display.get('reviewed_description') or {}
    values += reviewed.get('price_family_codes') or []
    return ' '.join(str(v) for v in values if v).upper()


STOP = set('MCB MCCB ACB RCCB RCBO TIMER RELAY CONTACTOR CHINT ELECTRIC SCHNEIDER MITSUBISHI OMRON CAD SOURCE FRONT SIDE VIEW SAMPLE MẪU THIẾT BỊ PROJECT LS'.split())


def family_tokens(identity):
    tokens = re.findall(r'[A-Z][A-Z0-9]*(?:[-_][A-Z0-9]+)*', identity)
    result = set()
    for word in tokens:
        for token in (compact(word), *(compact(s) for s in word.split('_')), *word.split('-')):
            # Alphabetic family names such as BKN are useful; generic device types aren't.
            if len(token) >= 3 and token not in STOP and re.match('[A-Z]', token):
                result.add(token)
    # CAD labels often insert a space between the model prefix and number.
    for prefix, number in re.findall(r'\b([A-Z]{1,8})\s+(\d+[A-Z0-9-]*)', identity):
        result.add(compact(prefix + number))
    result = {t for t in result if not (t.isalpha() and any(v.startswith(t) and len(v)>len(t) and v[len(t)].isdigit() for v in result))}
    return result


def matching_rows(raw, display, rows, category=None):
    """Return every compatible row in the best evidenced family, not one per brand."""
    identity = source_identity(raw, display)
    tokens = family_tokens(identity)
    brand = canonical_brand(raw.get('hang_xac_nhan') or display.get('brand') or '')
    spec = raw.get('thong_so') or {}
    ai = raw.get('nhan_dien_ai') or {}
    expected = str(category or (raw.get('source_catalog_review') or {}).get('component_type') or ai.get('source_component_type') or ai.get('loai_thiet_bi_code') or display.get('type') or '').upper()
    aliases = {'SELECTOR':'SELECTOR_SWITCH', 'INDICATOR':'LIGHT', 'PILOT_LIGHT':'LIGHT', 'THERMALRELAY':'THERMAL_RELAY', 'FUSEASSEMBLY':'FUSE_HOLDER', 'TERMINAL':'TERMINAL_BLOCK'}
    expected = aliases.get(expected, expected)
    normalize_category = category_key
    expected = normalize_category(expected)
    wanted = poles(spec.get('so_cuc') or spec.get('so_cuc_chinh') or spec.get('so_cuc_theo_nhan_hinh') or ai.get('so_cuc'))
    if not wanted:
        wanted = poles(identity)
    matches = []
    series_matches = []
    prefixes = {m[0] for t in tokens if (m := re.match(r'[A-Z]{2,}(?=\d)', t))}
    for row in rows:
        if brand and canonical_brand(row.get('brand')) != brand:
            continue
        actual_category = aliases.get(str(row.get('category') or '').upper(), str(row.get('category') or '').upper())
        actual_category = normalize_category(actual_category)
        if expected and actual_category != expected:
            continue
        actual = row_poles(row)
        if wanted and actual and wanted != actual:
            continue
        sku = compact(row.get('sku'))
        # Match a source family prefix, retaining every current/coil/contact variant.
        base = compact(re.split(r'[\s(/]', str(row.get('sku') or ''))[0])
        head = compact(re.split(r'[\s(/-]', str(row.get('sku') or ''))[0])
        matching = [t for t in tokens if (sku.startswith(t) and
                    (not t.isalpha() or (len(sku)>len(t) and sku[len(t)].isdigit())) and
                    not (t[-1].isdigit() and len(sku)>len(t) and sku[len(t)].isdigit() and head!=t)) or
                    (len(base) >= 5 and t == base + 'F')]
        score = max((len(t) for t in matching), default=0)
        basis = 'catalog_family_match'
        if ('TIMER' in identity and re.search(r'24\s*H', identity)
                and row.get('category') == 'TIMER'
                and re.search(r'24\s*H|24h', str(row.get('specifications') or {}) + str(row.get('group') or ''), re.I)):
            score = max(score, 4)
            basis = 'catalog_function_match'
        if score:
            matches.append((score, row, basis))
        elif brand and actual_category == expected and any(sku.startswith(prefix) for prefix in prefixes):
            series_matches.append((row, 'catalog_series_reference'))
    if not matches:
        return series_matches
    # A specific model beats a broad alphabetic prefix, while all its variants remain.
    best = max(m[0] for m in matches)
    return [(row, basis) for score, row, basis in matches if score == best]


def information_choice(row, basis):
    specs = dict(row.get('specifications') or {})
    if row.get('name') or row.get('item_name'):
        specs.setdefault('Tên hàng', row.get('item_name') or row['name'])
    if row_poles(row):
        specs.setdefault('Số cực', row_poles(row))
    return dict(brand=canonical_brand(row['brand']), model=row['sku'], specifications=specs,
                source_url=row.get('source_url') or '', source_label=row.get('source_label'),
                source_page=row.get('source_page'), source_row_id=row.get('id'),
                basis=basis, price='---', exact_cad_match=False,
                note=('Dòng liên quan cùng hãng và loại; khác mã/khung có thể khác kích thước. Chọn cấu hình theo bảng thông tin.'
                      if basis == 'catalog_series_reference' else
                      'Ghép theo hãng/dòng hoặc chức năng ghi trên CAD; chọn biến thể điện theo bảng thông tin.'))

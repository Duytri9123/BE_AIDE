"""Local, cited pricebook proposals kept separate from source identity.

Search priority: supplier_pricebooks (bảng giá, có liên kết) thay vì
library_catalog_information (thư viện thiết bị, chậm hơn và thiếu liên kết giá).
"""
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from app.schemas.ai import ExtractedDeviceSchema


def _strip_accents(text):
    norm = unicodedata.normalize('NFD', str(text or ''))
    return ''.join(c for c in norm if unicodedata.category(c) != 'Mn').replace('đ', 'd').replace('Đ', 'D')


# ---------------------------------------------------------------------------
# Parse rating numbers (hỗ trợ danh sách rời như "6,10,16" & số thập phân "0,5")
# ---------------------------------------------------------------------------

def _split_rating_list(text):
    def _expand(match):
        tokens = match.group(0).split(',')
        if len(tokens) > 2 or all(float(t) >= 10 for t in tokens):
            return ' '.join(tokens)
        return match.group(0)
    return re.sub(r'\d+(?:,\d+)+', _expand, str(text or ''))


def _numbers(value):
    if value is None:
        return set()
    cleaned = re.sub(r'\([^)]*\)', '', str(value))
    cleaned = _split_rating_list(cleaned)
    return {float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', cleaned)}


def _rating(spec, terms):
    return next(
        (v for k, v in spec.items()
         if any(term in _strip_accents(k).lower() for term in terms)),
        None,
    )


def _extract_row_currents(row):
    spec = row.get('specifications') or {}
    raw = _rating(spec, ['in (a)', 'dinh muc in', 'dong dinh muc (a)', 'dong dinh muc', 'rated current'])
    nums = _numbers(raw)
    if nums:
        return nums
    name = str(row.get('item_name') or row.get('name') or '')
    return {float(v.replace(',', '.')) for v in re.findall(r'(?<![\w-])(\d+(?:[.,]\d+)?)\s*A\b', name, re.I)}


def _extract_row_icu(row):
    spec = row.get('specifications') or {}
    raw = _rating(spec, ['icu', 'icn', 'kha nang cat'])
    if raw is None:
        return set()
    text = str(raw)
    ka = {float(v.replace(',', '.')) for v in re.findall(r'(\d+(?:[.,]\d+)?)\s*kA', text, re.I)}
    if ka:
        return ka
    if re.fullmatch(r'\s*\d+(?:[.,]\d+)?(?:\s*[/,-]\s*\d+(?:[.,]\d+)?)*\s*', text):
        return _numbers(text)
    return set()


def _extract_row_poles(row):
    from app.services.catalog_family_matching import row_poles
    pol = row_poles(row)
    if pol:
        return pol
    text = f"{row.get('item_name') or ''} {row.get('group') or ''}"
    m = re.search(r'(?<!\w)([1-4])\s*(?:P|POLES?)\b', text, re.I)
    return f'{m[1]}P' if m else ''


def _residual_currents(text, spec=None):
    values={float(v.replace(',', '.')) for v in re.findall(r'(\d+(?:[.,]\d+)?)\s*mA\b',str(text),re.I)}
    for key,value in (spec or {}).items():
        label=_strip_accents(key).lower()
        if 'ma' in label and any(term in label for term in ('idn','iδn','i∆n','dong ro','residual')):
            values.update(_numbers(value))
    return values


def _prepare_entry(row):
    return (
        row,
        _extract_row_currents(row),
        _extract_row_icu(row),
    )


# ---------------------------------------------------------------------------
# Index bảng giá để tìm kiếm nhanh O(1) thay vì linear scan O(n)
# ---------------------------------------------------------------------------

def _build_index(rows):
    from app.services.catalog_family_matching import category_key
    index = {}
    by_cat = {}
    for row in rows:
        cat = category_key(row.get('category') or '')
        pol = _extract_row_poles(row)
        entry = _prepare_entry(row)
        index.setdefault((cat, pol), []).append(entry)
        by_cat.setdefault(cat, []).append(entry)
    return index, by_cat


@lru_cache(maxsize=1)
def _pricebook_index(revision):
    """Build (category, poles) -> [(row, currents, icus)] index từ supplier_pricebooks."""
    from app.services.device_catalog_browser import load_supplier_items
    return _build_index(load_supplier_items())


def pricebook_index():
    """Trả về index được cache; tự invalidate khi file bảng giá thay đổi."""
    p = Path(__file__).resolve().parents[2] / 'data' / 'supplier_pricebooks.json'
    revision = (str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else ()
    return _pricebook_index((revision,))[0]


def _pricebook_indices():
    p = Path(__file__).resolve().parents[2] / 'data' / 'supplier_pricebooks.json'
    revision = (str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else ()
    return _pricebook_index((revision,))


# ---------------------------------------------------------------------------
# Category normalization & matching
# ---------------------------------------------------------------------------

GENERIC_BREAKER_CATEGORIES = {
    'APTOMAT', 'APTOMAT TEP', 'APTOMAT KHOI', 'BREAKER', 'CB',
    'CIRCUIT_BREAKER', 'CIRCUIT BREAKER', 'THIET BI DONG CAT', 'THIET BI BAO VE',
}
BREAKER_CATEGORIES = {'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB', 'ELCB'}
RATED_CATEGORIES = BREAKER_CATEGORIES | {'CONTACTOR', 'OVERLOAD', 'THERMAL_RELAY'}
AUXILIARY_PRICEBOOK_CATEGORIES = {'METER', 'SELECTOR_SWITCH', 'LIGHT', 'PILOT_LIGHT', 'INDICATOR_LIGHT', 'CT', 'SPD', 'RELAY', 'FUSE'}


def _normalize_device_category(device):
    raw_cat = _strip_accents(str(device.category or '')).upper().strip()
    if raw_cat in {'PROTECTIVE', 'MEASURING'}:
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        raw_cat = _strip_accents(normalize_scoped_row(device.model_dump())['category']).upper().strip()
    if raw_cat in {'PILOT_LIGHT', 'INDICATOR_LIGHT', 'DEN BAO', 'DEN BAO PHA'}:
        return 'LIGHT'
    if raw_cat in {'CHUYEN MACH', 'CONG TAC CHUYEN MACH'}:
        return 'SELECTOR_SWITCH'
    if raw_cat in {'DONG HO', 'DONG HO DO', 'AMMETER', 'VOLTMETER'}:
        return 'METER'
    if raw_cat in {'BIEN DONG'}:
        return 'CT'
    if raw_cat in {'PHU KIEN TU DIEN', 'ACCESSORY', ''}:
        text = _strip_accents(f"{device.name or ''} {device.spec or ''}").upper()
        if any(k in text for k in ('DEN BAO', 'R, Y, B', 'R,Y,B', 'PILOT', 'LAMP')):
            return 'LIGHT'
        if any(k in text for k in ('CHUYEN MACH', 'SELECTOR', 'VS ', 'AS ')):
            return 'SELECTOR_SWITCH'
        if any(k in text for k in ('DONG HO', 'VOLT', 'AMPE', 'METER', '0-600V', '0-500V')):
            return 'METER'
    if raw_cat in GENERIC_BREAKER_CATEGORIES or raw_cat.startswith(('APTOMAT', 'CIRCUIT')):
        spec_upper = _strip_accents(f"{device.name or ''} {device.spec or ''}").upper()
        for explicit in ('MCCB', 'RCBO', 'RCCB', 'ELCB', 'ACB', 'MCB'):
            if re.search(rf'\b{explicit}\b', spec_upper):
                return explicit
        return 'CB'
    return raw_cat


def _lookup_categories(norm_cat, in_a, icu_ka):
    if norm_cat == 'CB':
        if (in_a and in_a > 63) or (icu_ka and icu_ka > 10):
            return ['MCCB', 'CB', 'MCB']
        return ['MCB', 'CB', 'MCCB']
    if norm_cat == 'OVERLOAD':
        return ['THERMAL_RELAY', 'OVERLOAD']
    return [norm_cat]


def _match_auxiliary_row(norm_cat, device, row):
    dev_text = _strip_accents(f"{device.name or ''} {device.spec or ''}").lower()
    row_text = _strip_accents(
        f"{row.get('item_name') or ''} {row.get('group') or ''} {row.get('specifications') or ''}"
    ).lower()
    if norm_cat == 'METER':
        wants_volt = any(k in dev_text for k in ('volt', 'von', 'dien ap', '600v', '500v'))
        wants_amp = any(k in dev_text for k in ('ampe', 'amp', 'dong dien', '/5a'))
        if wants_volt and not wants_amp:
            return any(k in row_text for k in ('volt', 'von', 'dien ap', ' v ', '500v', '600v'))
        if wants_amp and not wants_volt:
            return any(k in row_text for k in ('ampe', 'amp', 'dong dien', '/5a'))
        return True
    if norm_cat == 'SELECTOR_SWITCH':
        wants_volt = any(k in dev_text for k in ('volt', 'von', 'dien ap', 'vs'))
        wants_amp = any(k in dev_text for k in ('ampe', 'amp', 'dong', 'as'))
        if wants_volt and not wants_amp:
            return any(k in row_text for k in ('volt', 'von', 'vs', 'dien ap'))
        if wants_amp and not wants_volt:
            return any(k in row_text for k in ('ampe', 'amp', 'as', 'dong'))
        return True
    if norm_cat == 'LIGHT':
        return any(k in row_text for k in ('den bao', 'pilot', 'lamp', 'led', 'phi 22', 'd22', '220v')) or True
    if norm_cat == 'CT':
        ratio = re.search(r'(\d+)\s*/\s*5', dev_text)
        if ratio:
            return f"{ratio[1]}/5" in row_text or f"{ratio[1]} / 5" in row_text
        return False
    if norm_cat == 'FUSE':
        currents = _extract_row_currents(row)
        return bool(device.in_a and device.in_a in currents)
    return True


def _candidate_dict(candidate, reason):
    return {
        'sku':                   candidate['sku'],
        'name':                  candidate.get('item_name') or candidate.get('name'),
        'source':                candidate.get('source_url') or '',
        'source_page':           candidate.get('source_page'),
        'price':                 candidate.get('price'),
        'price_row_id':          candidate.get('id'),
        'auto_selectable':       False,
        'requires_confirmation': True,
        'match_kind':            'pricebook_proposal',
        'reason':                reason,
    }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def suggest_takeoff_products(devices, engine=None, catalog_rows=None):
    from app.services.catalog_family_matching import category_key
    from app.services.ai.manufacturer_registry import canonical_brand

    # Chỉ dùng index bảng giá (supplier_pricebooks); không khởi tạo DeviceCatalogEngine nặng
    # trừ khi caller truyền vào engine đã có brand_index (giữ tương thích test/override).
    use_engine = engine is not None and bool(getattr(engine, 'brand_index', None))
    recommendations = None
    if use_engine:
        from app.services.ai.device_recommendations import recommendations

    if catalog_rows is None:
        idx, by_cat = _pricebook_indices()
    else:
        idx, by_cat = _build_index(catalog_rows)

    for row in devices:
        if row.get('catalog_candidates'):
            continue

        device = ExtractedDeviceSchema.model_validate(row)

        # Bổ sung thông số thiếu: parse từ cả name + spec + rated_current
        combined_text = f"{device.name or ''} {device.spec or ''}"
        # Hỗ trợ rated_current field (AI có thể gửi thay cho in_a)
        if not device.in_a and row.get('rated_current'):
            try:
                device.in_a = float(str(row['rated_current']).replace(',', '.').split()[0])
            except (ValueError, TypeError):
                pass
        for field, pattern in [
            ('in_a',   r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\b'),
            ('poles',  r'\b([1-4])\s*[Pp]\b'),
            ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\b'),
        ]:
            if not getattr(device, field):
                m = re.search(pattern, combined_text, re.I)
                if m:
                    setattr(
                        device,
                        field,
                        int(m[1]) if field == 'poles' else float(m[1].replace(',', '.')),
                    )
        # Phase count is circuit information; it does not establish pole count.

        norm_cat = _normalize_device_category(device)
        choices = recommendations(engine, device, device.brand) if use_engine else {}

        # Nhánh 1: Thiết bị đo lường / đèn báo / chuyển mạch / CT / SPD trong bảng giá
        if norm_cat in AUXILIARY_PRICEBOOK_CATEGORIES:
            cat_key = category_key(norm_cat)
            seen_skus = set()
            for candidate, _, _ in by_cat.get(cat_key, []):
                sku = candidate.get('sku')
                source = candidate.get('source_url') or ''
                if not sku or not source or sku in seen_skus:
                    continue
                if not _match_auxiliary_row(norm_cat, device, candidate):
                    continue
                seen_skus.add(sku)
                brand = canonical_brand(candidate.get('brand'))
                choices.setdefault(brand, []).append(_candidate_dict(
                    candidate,
                    'Bảng giá ghi cùng loại thiết bị/chức năng; cần đối chiếu điện áp, kích thước lỗ khoét và mã đặt hàng trước khi chọn.',
                ))
        else:
            # Nhánh 2: Thiết bị đóng cắt / bảo vệ (MCB, MCCB, CB/APTOMAT, ACB, RCBO, RCCB, ELCB, CONTACTOR, OVERLOAD)
            needs_poles = norm_cat in (BREAKER_CATEGORIES | {'CB'})
            if norm_cat not in (RATED_CATEGORIES | {'CB'}):
                row['selection_analysis'] = {'status':'no_verified_catalog_match',
                    'reason':'Chưa có mã bảng giá được đối chiếu đúng loại và chức năng của thiết bị này.'}
                continue
            if not device.in_a or (needs_poles and not device.poles):
                row['selection_analysis'] = {
                    'status': 'insufficient_source_specs',
                    'reason': 'Chưa đủ loại thiết bị, số cực hoặc dòng định mức để gợi ý mã có căn cứ.',
                }
                continue

            from app.services.catalog_family_matching import poles as source_poles
            pol_key = source_poles(combined_text) or (f'{device.poles}P' if device.poles else '')
            search_cats = _lookup_categories(norm_cat, device.in_a, device.icu_ka)
            seen_skus = set()

            for target_cat in search_cats:
                cat_key = category_key(target_cat)
                bucket = idx.get((cat_key, pol_key), []) if pol_key else by_cat.get(cat_key, [])
                for candidate, currents, icus in bucket:
                    if device.in_a not in currents:
                        continue
                    if device.icu_ka and (not icus or max(icus) < device.icu_ka):
                        continue
                    residual = _residual_currents(combined_text)
                    if residual and not residual.issubset(_residual_currents(
                            candidate.get('item_name') or candidate.get('name') or '',candidate.get('specifications'))):
                        continue

                    sku = candidate.get('sku')
                    source = candidate.get('source_url') or ''
                    if not sku or not source or sku in seen_skus:
                        continue

                    seen_skus.add(sku)
                    brand = canonical_brand(candidate.get('brand'))
                    choices.setdefault(brand, []).append(_candidate_dict(
                        candidate,
                        'Bảng giá ghi cùng loại, số cực, dòng và khả năng cắt; '
                        'cần đối chiếu điện áp, đặc tính và mã đặt hàng/biến thể trước khi chọn.',
                    ))

        cited = {
            brand: [c for c in cands if c.get('sku') and c.get('source')][:3]
            for brand, cands in choices.items()
        }
        row['catalog_candidates'] = {b: c for b, c in cited.items() if c}
        row['suggested_brands']   = list(row['catalog_candidates'])
        row['selection_analysis'] = {
            'status': 'proposals' if row['catalog_candidates'] else 'no_verified_catalog_match',
            'reason': (
                'Mã tham khảo đối chiếu bảng giá; chưa chọn thay cho thiết bị trên bản vẽ.'
                if row['catalog_candidates']
                else 'Chưa tìm được mã có nguồn bảng giá phù hợp với thông số đã đọc.'
            ),
        }

    return devices

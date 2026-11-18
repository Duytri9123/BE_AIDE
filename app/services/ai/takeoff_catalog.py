"""Local, cited catalog proposals kept separate from source identity.

Search priority: supplier_pricebooks (bảng giá, có liên kết) thay vì
library_catalog_information (thư viện thiết bị, chậm hơn và thiếu liên kết giá).
"""
import re
from functools import lru_cache
from app.schemas.ai import ExtractedDeviceSchema


# ---------------------------------------------------------------------------
# Index bảng giá để tìm kiếm nhanh O(1) thay vì linear scan O(n)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _pricebook_index(revision):
    """Build (category, poles) → [rows] index từ supplier_pricebooks."""
    from app.services.device_catalog_browser import load_supplier_items
    from app.services.catalog_family_matching import category_key, row_poles

    rows = load_supplier_items()
    index = {}
    for row in rows:
        cat = category_key(row.get('category') or '')
        pol = row_poles(row)                    # e.g. "1P", "3P", ""
        key = (cat, pol)
        index.setdefault(key, []).append(row)
    return index


def pricebook_index():
    """Trả về index được cache; tự invalidate khi file thay đổi."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / 'data' / 'supplier_pricebooks.json'
    revision = (str(p), p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else ()
    return _pricebook_index((revision,))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _numbers(value):
    return {float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', str(value))}


def _rating(spec, terms):
    from app.services.device_catalog_engine import strip_accents
    return next(
        (v for k, v in spec.items()
         if any(term in strip_accents(k).lower() for term in terms)),
        None,
    )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def suggest_takeoff_products(devices, engine=None, catalog_rows=None):
    from app.services.device_catalog_engine import DeviceCatalogEngine
    from app.services.ai.device_recommendations import recommendations
    from app.services.catalog_family_matching import category_key, row_poles
    from app.services.ai.manufacturer_registry import canonical_brand

    engine = engine or DeviceCatalogEngine.get_instance()

    # Dùng index bảng giá thay vì source_rows() từ thư viện thiết bị
    # catalog_rows vẫn được nhận làm override khi caller truyền vào
    use_index = catalog_rows is None
    if use_index:
        idx = pricebook_index()
    else:
        # Fallback: build index tạm từ danh sách được truyền vào
        idx = {}
        for row in catalog_rows:
            cat = category_key(row.get('category') or '')
            pol = row_poles(row)
            idx.setdefault((cat, pol), []).append(row)

    for row in devices:
        if row.get('catalog_candidates'):
            continue

        device = ExtractedDeviceSchema.model_validate(row)

        # Bổ sung thông số thiếu từ trường spec
        for field, pattern in [
            ('in_a',   r'(?<![\d.])([\d]+(?:[.,]\d+)?)\s*A\b'),
            ('poles',  r'\b([1-4])\s*P\b'),
            ('icu_ka', r'(?<![\d.])([\d]+(?:[.,]\d+)?)\s*kA\b'),
        ]:
            m = re.search(pattern, device.spec, re.I)
            if not getattr(device, field) and m:
                setattr(device, field,
                        int(m[1]) if field == 'poles'
                        else float(m[1].replace(',', '.')))

        if (device.category not in
                {'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB', 'CONTACTOR', 'OVERLOAD'}
                or not device.in_a or not device.poles):
            row['selection_analysis'] = {
                'status': 'insufficient_source_specs',
                'reason': 'Chưa đủ loại thiết bị, số cực hoặc dòng định mức để gợi ý mã có căn cứ.',
            }
            continue

        choices = recommendations(engine, device, device.brand)

        # Tra cứu nhanh theo (category, poles) trong bảng giá
        cat_key = category_key(device.category)
        pol_key = str(device.poles) + 'P'
        candidates = idx.get((cat_key, pol_key), [])

        for candidate in candidates:
            spec = candidate.get('specifications') or {}
            current  = _rating(spec, ['in (a)', 'dinh muc in', 'dong dinh muc (a)', 'dong dinh muc'])
            breaking = _rating(spec, ['icu', 'icn', 'kha nang cat'])

            if device.in_a not in _numbers(current):
                continue
            if device.icu_ka and (
                not _numbers(breaking)
                or min(_numbers(breaking)) < device.icu_ka
            ):
                continue

            # Chấp nhận cả URL nội bộ (/device-catalog/...) và URL ngoài (https://...)
            source = candidate.get('source_url') or ''
            has_source = bool(source)   # bảng giá luôn có source_url

            if not candidate.get('sku') or not has_source:
                continue

            brand = canonical_brand(candidate.get('brand'))
            choices.setdefault(brand, []).append({
                'sku':                 candidate['sku'],
                'name':                candidate.get('item_name') or candidate.get('name'),
                'source':              source,
                'source_page':         candidate.get('source_page'),
                'price':               candidate.get('price'),
                'price_row_id':        candidate.get('id'),
                'auto_selectable':     False,
                'requires_confirmation': True,
                'match_kind':          'pricebook_proposal',
                'reason':              (
                    'Bảng giá ghi cùng loại, số cực, dòng và khả năng cắt; '
                    'cần đối chiếu điện áp, đặc tính và mã đặt hàng/biến thể trước khi chọn.'
                ),
            })

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

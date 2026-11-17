"""Local, cited catalog proposals kept separate from source identity."""
import re
from app.schemas.ai import ExtractedDeviceSchema


def suggest_takeoff_products(devices, engine=None, catalog_rows=None):
    from app.services.device_catalog_engine import DeviceCatalogEngine
    from app.services.ai.device_recommendations import recommendations
    engine = engine or DeviceCatalogEngine.get_instance()
    from app.services.library_catalog_information import source_rows
    from app.services.catalog_family_matching import category_key, row_poles
    from app.services.device_catalog_engine import strip_accents
    from app.services.ai.manufacturer_registry import canonical_brand
    catalog_rows = source_rows() if catalog_rows is None else catalog_rows
    def numbers(value):
        return {float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', str(value))}
    def rating(spec, terms):
        return next((v for k,v in spec.items() if any(term in strip_accents(k).lower() for term in terms)), None)
    for row in devices:
        if row.get('catalog_candidates'):
            continue
        device = ExtractedDeviceSchema.model_validate(row)
        for field, pattern in [('in_a', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*A\b'),
                               ('poles', r'\b([1-4])\s*P\b'),
                               ('icu_ka', r'(?<![\d.])(\d+(?:[.,]\d+)?)\s*kA\b')]:
            match = re.search(pattern, device.spec, re.I)
            if not getattr(device, field) and match:
                setattr(device, field, int(match[1]) if field == 'poles' else float(match[1].replace(',', '.')))
        if device.category not in {'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB', 'CONTACTOR', 'OVERLOAD'} or not device.in_a or not device.poles:
            row['selection_analysis'] = {'status': 'insufficient_source_specs',
                'reason': 'Chưa đủ loại thiết bị, số cực hoặc dòng định mức để gợi ý mã có căn cứ.'}
            continue
        choices = recommendations(engine, device, device.brand)
        # The priced engine may have no approved variants. Published catalog rows
        # still provide documented options; price availability is not identity evidence.
        for candidate in catalog_rows:
            spec = candidate.get('specifications') or {}
            if category_key(candidate.get('category')) != device.category or row_poles(candidate) != str(device.poles)+'P':
                continue
            current = rating(spec, ['in (a)', 'dinh muc in', 'dong dinh muc (a)', 'dong dinh muc'])
            breaking = rating(spec, ['icu', 'icn', 'kha nang cat'])
            if device.in_a not in numbers(current) or (device.icu_ka and (not numbers(breaking) or min(numbers(breaking)) < device.icu_ka)):
                continue
            source = candidate.get('source_url')
            if not candidate.get('sku') or not str(source or '').startswith(('https://','http://')):
                continue
            brand = canonical_brand(candidate.get('brand'))
            choices.setdefault(brand, []).append({'sku': candidate['sku'], 'name': candidate.get('item_name') or candidate.get('name'),
                'source': source, 'source_page': candidate.get('source_page'), 'price': candidate.get('price'),
                'auto_selectable': False, 'requires_confirmation': True, 'match_kind': 'catalog_proposal',
                'reason': 'Catalog ghi cùng loại, số cực, dòng và khả năng cắt; cần đối chiếu điện áp, đặc tính và mã đặt hàng/biến thể trước khi chọn.'})
        cited = {brand: [c for c in candidates if c.get('sku') and c.get('source')][:3]
                 for brand, candidates in choices.items()}
        row['catalog_candidates'] = {brand: candidates for brand, candidates in cited.items() if candidates}
        row['suggested_brands'] = list(row['catalog_candidates'])
        row['selection_analysis'] = {'status': 'proposals' if row['catalog_candidates'] else 'no_verified_catalog_match',
            'reason': 'Mã tham khảo đối chiếu catalog; chưa chọn thay cho thiết bị trên bản vẽ.' if row['catalog_candidates']
                else 'Chưa tìm được mã có nguồn catalog phù hợp với thông số đã đọc.'}
    return devices

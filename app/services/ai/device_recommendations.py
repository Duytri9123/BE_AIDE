"""Catalog evidence for manual comparison; brand preference never overrides function."""
from app.services.device_catalog_engine import strip_accents


def recommendations(engine, device, preferred_brand=None):
    kind = str(device.category or '').upper()
    text = strip_accents(f"{device.name or ''} {device.spec or ''}").upper()
    function_terms = []
    if kind == 'METER':
        for triggers, terms in [(['KWH', 'CONG TO'], ['KWH', 'CONG TO']),
                                (['AMPE'], ['AMPE', 'AMMETER']),
                                (['VON', 'VOLT'], ['VON', 'VOLT']),
                                (['DA NANG', 'MFM'], ['DA NANG', 'MFM'])]:
            if any(t in text for t in triggers):
                function_terms = terms
                break
    if kind == 'TIMER' and any(t in text for t in ['LUAN PHIEN', 'ALTERNAT', 'CYCLIC']):
        function_terms = ['LUAN PHIEN', 'ALTERNAT', 'CYCLIC']
    result = {}
    for brand in engine.brand_index:
        rows = engine.search_candidates(brand=brand, device_type=kind, poles=device.poles,
            in_current=device.in_a or None, min_icu=device.icu_ka or None, limit=50)
        candidates = []
        for row in rows:
            label = strip_accents(f"{row.get('n', '')} {row.get('ma', '')}").upper()
            if function_terms and not any(t in label for t in function_terms):
                continue
            complete = all(row.get(k) is not None for k, value in
                [('p', device.poles), ('in', device.in_a), ('icu', device.icu_ka)] if value)
            # Parametric matches remain proposals until voltage, function and exact
            # purchasable variant have been confirmed; missing ratings never auto-select.
            candidates.append({'sku': row.get('ma') or '', 'name': row.get('n') or '',
                'price': row.get('g'), 'icu_ka': row.get('icu'),
                'catalog_id': row.get('catalog_id'), 'source': row.get('source'),
                'rating_complete': complete, 'auto_selectable': False,
                'reason': f"Catalog {brand}: đúng nhóm {kind}" +
                    (f", {device.poles} cực" if device.poles else '') +
                    (f", {device.in_a:g} A" if device.in_a and row.get('in') is not None else '') +
                    (f", khả năng cắt ≥ {device.icu_ka:g} kA" if device.icu_ka else '') +
                    '. Cần xác nhận điện áp, chức năng và biến thể mã trước khi chốt.'})
        if candidates:
            result[brand] = sorted(candidates, key=lambda c: (not bool(c['price']), -(c['price'] or 0)))
    # CAD/source families remain visible even when no verified price variants
    # exist. Never invent a SKU or price from a family label.
    if hasattr(engine, 'search_references'):
        refs = engine.search_references(kind, poles=device.poles, limit=100, query=device.name, group_views=True)
        for ref in refs:
            label = strip_accents(str(ref.get('name') or '')).upper()
            if function_terms and not any(t in label for t in function_terms):
                continue
            brand = ref.get('brand') or 'Chưa xác định hãng'
            result.setdefault(brand, []).append({
                'sku': '', 'name': ref.get('name') or ref.get('series') or '',
                'price': None, 'catalog_id': ref.get('reference_path'),
                'source': ref.get('reference_path'), 'rating_complete': False,
                'auto_selectable': False,
                'reason': ref.get('selection_note') or 'Tài liệu dòng thiết bị; cần chọn biến thể, xác minh thông số và bổ sung giá.'})
    return result

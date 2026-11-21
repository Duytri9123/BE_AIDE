"""Apply a preferred maker only where the published catalog verifies a replacement."""
from copy import deepcopy

from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.quotation_selection import select_quotation_devices


def compatible_brand_replacements(devices, brand, rows=None):
    proposals = select_quotation_devices(devices, brand, rows)
    result, changed = [], 0
    c_brand = canonical_brand(brand)
    for original, proposal in zip(devices, proposals):
        match = proposal.get('pricebook_match') or {}
        product = proposal.get('selected_product') or {}

        # 1. Nếu chưa có selected_product từ bảng giá, tìm trong catalog_candidates sẵn có của thiết bị
        if not product.get('sku'):
            candidates = []
            for b_key, b_cands in (original.get('catalog_candidates') or {}).items():
                if canonical_brand(b_key) == c_brand and isinstance(b_cands, list) and b_cands:
                    candidates = b_cands
                    break
            if candidates:
                best = next((c for c in candidates if c.get('auto_selectable') and c.get('rating_complete') is not False), candidates[0])
                product = best
                proposal['selected_product'] = product
                proposal['brand'] = product.get('brand') or brand

        # Giữ lại và gộp toàn bộ catalog_candidates của các hãng khác, không làm mất danh sách hãng
        merged_candidates = deepcopy(original.get('catalog_candidates') or {})
        for k, v in (proposal.get('catalog_candidates') or {}).items():
            merged_candidates[k] = v
        proposal['catalog_candidates'] = merged_candidates

        # 2. Nếu có sản phẩm khớp hãng được chọn (kể cả chưa có bảng giá)
        if product.get('sku') and canonical_brand(product.get('brand') or proposal.get('brand')) == c_brand:
            proposal['brand'] = product.get('brand') or brand
            proposal['sku'] = product['sku']
            proposal['part_number'] = product['sku']
            proposal['selection_source'] = 'user_request'
            proposal['unit_price'] = product.get('price')
            proposal['price'] = product.get('price')
            result.append(proposal)
            changed += 1
            continue

        # 3. Nếu chưa tìm được mã catalog cho hãng này, vẫn cập nhật brand theo lựa chọn của người dùng
        updated = deepcopy(original)
        updated['brand'] = brand
        updated['catalog_candidates'] = merged_candidates
        result.append(updated)
    return result, changed

"""Utilities to separate and normalize Fuses and Pilot Lights in Takeoff."""
from copy import deepcopy
import re
from app.services.ai.standard_device_catalog import get_standard_candidates

def split_and_normalize_metering_pilot_lights(devices: list[dict]) -> list[dict]:
    """
    Tách biệt hoàn toàn Cầu chì bảo vệ (FUSE) và Đèn báo pha (PILOT_LIGHT / LIGHT):
    - Khi bóc tách hoặc AI gộp thành 1 dòng (ví dụ 'Bộ hiển thị đo lường và đèn báo pha (3x2A-250V Đ V X)'):
      BẮT BUỘC TÁCH THÀNH 2 DÒNG ĐỘC LẬP:
      1) Cầu chì hạ thế bảo vệ đèn báo pha (FUSE, 2A-250V, 3 Cái, section 'Đo lường & Giám sát')
      2) Đèn báo pha (PILOT_LIGHT / LIGHT, 220V/250V, 3 Cái, section 'Đo lường & Giám sát')
    - Đảm bảo đèn báo pha và cầu chì luôn có section là 'Đo lường & Giám sát', không bị None.
    - Gộp các đèn báo pha lẻ (Đỏ, Vàng, Xanh) thành 1 dòng bộ 3 đèn báo pha Đ-V-X cho gọn gàng và chuẩn báo giá.
    """
    res: list[dict] = []
    lamps_to_combine: list[dict] = []
    
    for d in devices:
        row = deepcopy(d)
        n = str(row.get('name') or '').lower()
        s = str(row.get('spec') or '').lower()
        c = str(row.get('category') or '').upper()
        obs = str(row.get('observed_text') or '').lower()

        # Kiểm tra xem dòng này có bị gộp Cầu chì + Đèn báo pha hay không
        is_merged = (
            ('đo lường và đèn báo' in n or ('cầu chì' in n and 'đèn báo' in n))
            or ('3x2a' in s and any(k in s for k in ('đ v x', 'd v x', 'đèn', 'pha')))
            or ('3x2a' in obs and any(k in obs for k in ('đ v x', 'd v x', 'đèn', 'pha')))
            or (c in {'LIGHT', 'PILOT_LIGHT'} and '3x2a' in s)
        )

        if is_merged:
            # 1. Dòng Cầu chì bảo vệ
            fuse_row = deepcopy(row)
            fuse_candidates = get_standard_candidates('FUSE', '2A-250V', 'Cầu chì hạ thế', 1, 2.0, None)
            fuse_row.update({
                'name': 'Cầu chì hạ thế bảo vệ đèn báo pha',
                'device_type': 'Cầu chì hạ thế',
                'category': 'FUSE',
                'spec': '2A-250V',
                'observed_text': '3x2A-250V',
                'in_a': 2.0,
                'voltage_v': 250.0,
                'quantity': 3,
                'unit': 'Cái',
                'tag': 'FU',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': '03 Cầu chì 2A-250V bảo vệ ngắn mạch và quá dòng cho nhánh đèn báo pha 3 pha nguồn tổng.'
            })
            if fuse_candidates and not fuse_row.get('catalog_candidates'):
                fuse_row['catalog_candidates'] = fuse_candidates
                first_brand = next(iter(fuse_candidates.keys()), None)
                if first_brand and fuse_candidates[first_brand]:
                    fuse_row['suggested_sku'] = fuse_candidates[first_brand][0].get('sku')
                    if not fuse_row.get('brand'):
                        fuse_row['brand'] = first_brand
            res.append(fuse_row)

            # 2. Dòng Đèn báo pha
            light_row = deepcopy(row)
            light_candidates = get_standard_candidates('LIGHT', '220V', 'Đèn báo pha', 1, None, None)
            light_row.update({
                'name': 'Đèn báo pha (Đỏ, Vàng, Xanh)',
                'device_type': 'Đèn báo pha',
                'category': 'PILOT_LIGHT',
                'spec': '220V/250V',
                'observed_text': 'Đ V X',
                'in_a': None,
                'voltage_v': 220.0,
                'quantity': 3,
                'unit': 'Cái',
                'tag': 'HL',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': '03 Đèn báo pha (Đỏ, Vàng, Xanh) 220VAC giám sát sự hiện diện điện áp 3 pha nguồn tổng.'
            })
            if light_candidates and not light_row.get('catalog_candidates'):
                light_row['catalog_candidates'] = light_candidates
                first_brand = next(iter(light_candidates.keys()), None)
                if first_brand and light_candidates[first_brand]:
                    light_row['suggested_sku'] = light_candidates[first_brand][0].get('sku')
                    if not light_row.get('brand'):
                        light_row['brand'] = first_brand
            res.append(light_row)

        elif c in {'PILOT_LIGHT', 'LIGHT'} or 'đèn báo pha' in n or 'báo pha' in n:
            row['section'] = 'Đo lường & Giám sát'
            row['category'] = 'PILOT_LIGHT'
            if any(color in n for color in ('đỏ', 'vàng', 'xanh')):
                lamps_to_combine.append(row)
            else:
                if '3x' in s or '3 đèn' in n:
                    row['quantity'] = 3
                if not row.get('spec') or row['spec'] in {'None', 'chưa xác định'}:
                    row['spec'] = '220V/250V'
                res.append(row)

        elif c in {'FUSE', 'FUSE_HOLDER'} or 'cầu chì' in n:
            row['section'] = 'Đo lường & Giám sát'
            row['category'] = 'FUSE'
            if '3x' in s or '3x' in obs or '3' in str(row.get('quantity') or ''):
                row['quantity'] = 3
            if not row.get('spec') or row['spec'] in {'None', 'chưa xác định'}:
                row['spec'] = '2A-250V'
            res.append(row)

        else:
            res.append(row)

    if lamps_to_combine:
        # Nếu chưa có đèn báo pha nào trong res thì mới gộp thêm vào
        has_pilot_light = any(r.get('category') in {'PILOT_LIGHT', 'LIGHT'} for r in res)
        if not has_pilot_light:
            base = lamps_to_combine[0]
            combined_lamp = deepcopy(base)
            combined_lamp.update({
                'name': 'Đèn báo pha (Đỏ, Vàng, Xanh)',
                'device_type': 'Đèn báo pha',
                'category': 'PILOT_LIGHT',
                'spec': '220V/250V',
                'quantity': max(3, sum(l.get('quantity') or 1 for l in lamps_to_combine)),
                'unit': 'Cái',
                'tag': 'HL',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': '03 Đèn báo pha (Đỏ, Vàng, Xanh) 220VAC giám sát sự hiện diện điện áp 3 pha nguồn tổng.'
            })
            res.append(combined_lamp)

    return res

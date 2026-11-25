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

        # Nhận diện tổng quát dòng bị gộp giữa Cầu chì bảo vệ (FUSE) và Đèn báo pha (LIGHT / PILOT_LIGHT)
        combined_text = f"{n} {s} {obs}"
        has_fuse = any(k in combined_text for k in ('cầu chì', 'cau chi', 'fuse', 'fu')) or bool(re.search(r'\b\d+x?\d+a\b', combined_text))
        has_light = any(k in combined_text for k in ('đèn', 'den', 'báo pha', 'bao pha', 'pilot', 'light', 'đ v x', 'd v x', 'r s t', 'r-s-t', 'r y b')) or c in {'LIGHT', 'PILOT_LIGHT'}
        is_merged = (
            ('đo lường và đèn báo' in n or ('cầu chì' in n and 'đèn báo' in n))
            or (has_fuse and has_light and not (c == 'FUSE' and not any(k in combined_text for k in ('đèn', 'pha', 'light'))))
            or (c in {'LIGHT', 'PILOT_LIGHT'} and bool(re.search(r'\b\d+x?\d+a\b', combined_text)))
        )

        if is_merged:
            # Trích xuất linh hoạt thông số dòng, áp, số pha từ văn bản nguồn
            amp_match = re.search(r'(\d+(?:\.\d+)?)\s*a\b', combined_text, re.IGNORECASE)
            amp_val = float(amp_match.group(1)) if amp_match else 2.0
            
            volt_match = re.search(r'(\d+)\s*v\b', combined_text, re.IGNORECASE)
            volt_val = float(volt_match.group(1)) if volt_match else 250.0

            phase_match = re.search(r'(\d+)\s*x', combined_text, re.IGNORECASE)
            is_three_phase = bool(phase_match and int(phase_match.group(1)) == 3) or any(k in combined_text for k in ('đ v x', 'd v x', 'r s t', 'r-s-t', 'r y b', '3 pha', '3 đèn'))
            qty = int(phase_match.group(1)) if phase_match else (3 if is_three_phase else 1)

            amp_str = f"{int(amp_val) if amp_val.is_integer() else amp_val}A"
            volt_str = f"{int(volt_val)}V"
            fuse_spec = f"{amp_str}-{volt_str}"

            # 1. Dòng Cầu chì bảo vệ
            fuse_row = deepcopy(row)
            fuse_candidates = get_standard_candidates('FUSE', fuse_spec, 'Cầu chì hạ thế', 1, amp_val, None)
            fuse_row.update({
                'name': f'Cầu chì bảo vệ mạch đo lường & đèn báo ({fuse_spec})',
                'device_type': 'Cầu chì hạ thế',
                'category': 'FUSE',
                'spec': fuse_spec,
                'observed_text': f"{qty}x{fuse_spec}",
                'in_a': amp_val,
                'voltage_v': volt_val,
                'quantity': qty,
                'unit': 'Cái',
                'tag': 'FU',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': f'{qty:02d} Cầu chì {fuse_spec} bảo vệ ngắn mạch và quá dòng cho nhánh đo lường/đèn báo.'
            })
            if fuse_candidates and not fuse_row.get('catalog_candidates'):
                fuse_row['catalog_candidates'] = fuse_candidates
                existing_brand = fuse_row.get('brand')
                if existing_brand and existing_brand in fuse_candidates:
                    fuse_row['suggested_sku'] = fuse_candidates[existing_brand][0].get('sku')
            res.append(fuse_row)

            # 2. Dòng Đèn báo pha
            light_row = deepcopy(row)
            light_candidates = get_standard_candidates('LIGHT', '220V', 'Đèn báo pha', 1, None, None)
            light_spec = 'Đèn báo pha'
            light_row.update({
                'name': 'Đèn báo pha',
                'device_type': 'Đèn báo pha',
                'category': 'PILOT_LIGHT',
                'spec': light_spec,
                'observed_text': 'Đèn báo pha',
                'in_a': None,
                'voltage_v': 220.0,
                'quantity': qty,
                'unit': 'Cái',
                'tag': 'HL',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': f'{qty:02d} Đèn báo pha giám sát sự hiện diện điện áp các pha nguồn tổng.'
            })
            if light_candidates and not light_row.get('catalog_candidates'):
                light_row['catalog_candidates'] = light_candidates
                existing_brand = light_row.get('brand')
                if existing_brand and existing_brand in light_candidates:
                    light_row['suggested_sku'] = light_candidates[existing_brand][0].get('sku')
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
                'name': 'Đèn báo pha',
                'device_type': 'Đèn báo pha',
                'category': 'PILOT_LIGHT',
                'spec': 'Đèn báo pha',
                'quantity': max(3, sum(l.get('quantity') or 1 for l in lamps_to_combine)),
                'unit': 'Cái',
                'tag': 'HL',
                'section': 'Đo lường & Giám sát',
                'technical_analysis': '03 Đèn báo pha giám sát sự hiện diện điện áp 3 pha nguồn tổng.'
            })
            res.append(combined_lamp)

    return res

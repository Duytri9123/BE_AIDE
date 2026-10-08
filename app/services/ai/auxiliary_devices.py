"""Expose evidenced, quantified auxiliary devices to CAD selection and BOM."""
import unicodedata
from app.services.cad.catalogtb_assets import candidates


def _normal(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower())
                   if not unicodedata.combining(c)).replace('đ', 'd').strip()


def expand_devices(devices):
    rows = [dict(d) if isinstance(d, dict) else d.model_dump() for d in devices]
    result = []
    for device in rows:
        retained, extras = [], []
        if device.get('category') == 'METER' and 'chuyen mach' in _normal(device.get('quantity_basis', '')):
            if not any(r.get('category') == 'SELECTOR' and r.get('panel_code') == device.get('panel_code')
                       for r in rows + result):
                refs = candidates('SELECTOR')
                extras.append(dict(category='SELECTOR', name='Chuyển mạch vôn kế', tag='VS',
                                   quantity=device.get('quantity', 1), spec='', panel_code=device.get('panel_code'),
                                   panel_name=device.get('panel_name'), source_filename=device.get('source_filename'),
                                   source_page=device.get('source_page'), quantity_basis=device['quantity_basis'],
                                   section='Đo lường & Giám sát', accompanying_accessories=[],
                                   notes='Xác nhận mua rời hay theo bộ vôn kế để tránh tính trùng.',
                                   cad={'requires_selection': True, 'reference_candidates':
                                        [{k: r[k] for k in ('id', 'name', 'face', 'profile_path', 'status')} for r in refs]}))
        for accessory in device.get('accompanying_accessories') or []:
            if not isinstance(accessory, dict):
                retained.append(accessory)
                continue
            name = str(accessory.get('name') or '')
            key = _normal(name)
            category = ('METER' if 'von' in key else 'LIGHT' if 'den bao' in key
                        else 'FUSE' if 'cau chi' in key else None)
            evidence = (accessory.get('evidence') or accessory.get('sld_evidence')
                        or accessory.get('source_reference'))
            qty = accessory.get('quantity')
            if not category or not evidence or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
                retained.append(accessory)
                continue
            # A category alone does not identify a component: two lamp groups may coexist.
            existing = any(r.get('panel_code') == device.get('panel_code')
                           and r.get('category') == category
                           and _normal(r.get('name', '')) == key
                           and str(r.get('quantity_basis', '')) == str(evidence)
                           for r in rows + result + extras)
            if existing:
                continue
            refs = candidates('FUSE_HOLDER' if category == 'FUSE' else category)
            refs = [r for r in refs if qty % int(r.get('components_per_asset') or 1) == 0]
            extras.append(dict(
                category=category, name=name, spec=accessory.get('spec') or '',
                quantity=qty, procurement_quantity=qty,
                panel_code=device.get('panel_code'), panel_name=device.get('panel_name'),
                tag={'METER': 'V', 'LIGHT': 'R-Y-B', 'FUSE': 'FU'}[category],
                section='Đo lường & Giám sát', quantity_basis=str(evidence),
                source_filename=device.get('source_filename'), source_page=device.get('source_page'),
                accompanying_accessories=[],
                notes='Thiết bị độc lập tách từ cụm phụ kiện; mã mua hàng cần đối chiếu.',
                cad={'reference_candidates': [{k: r[k] for k in ('id', 'name', 'face', 'profile_path', 'status')}
                                              for r in refs], 'requires_selection': True}))
            if category == 'METER' and 'chuyen mach' in _normal(evidence):
                if not any(r.get('category') == 'SELECTOR' and r.get('panel_code') == device.get('panel_code')
                           for r in rows + result + extras):
                    selector_refs = candidates('SELECTOR')
                    selector = dict(extras[-1], category='SELECTOR', name='Chuyển mạch vôn kế',
                                    tag='VS', spec='', quantity=qty, procurement_quantity=qty,
                                    notes='Sơ đồ ghi kèm chuyển mạch; xác nhận mua rời hay theo bộ để tránh tính trùng.',
                                    cad={'reference_candidates': [{k: r[k] for k in ('id', 'name', 'face', 'profile_path', 'status')}
                                                                  for r in selector_refs], 'requires_selection': True})
                    extras.append(selector)
        device['accompanying_accessories'] = retained
        result.append(device)
        result.extend(extras)
    return result

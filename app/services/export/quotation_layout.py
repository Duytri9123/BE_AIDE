"""Commercial table layout shared by saved quotations and Excel exports."""
from copy import deepcopy
import re
import unicodedata

PACKAGES = (
    ('ENCLOSURE', 'Vỏ tủ điện', 'Cái'),
    ('BUSBAR', 'Đồng thanh cái mạ thiếc bọc co nhiệt', 'Tủ'),
    ('MATERIALS', 'Vật tư phụ (đầu cos, dây điều khiển, sứ …)', 'Tủ'),
    ('LABOR', 'Nhân công lắp ráp tủ', 'Tủ'),
)


def plain(value):
    value = str(value or '').lower().replace('đ', 'd').replace('*', '').strip()
    return ''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c))


def is_assembly(value):
    return bool(re.fullmatch(r'vo tu\s*[+&]\s*phu kien', plain(value)))


def package_code(row):
    if row.get('package_code') in {p[0] for p in PACKAGES}:
        return row['package_code']
    name = plain(row.get('name'))
    for code, pattern in (
        ('ENCLOSURE', r'^vo tu'),
        ('BUSBAR', r'dong thanh cai|thanh cai dong|busbar'),
        ('LABOR', r'nhan cong|lap rap va kiem tra'),
        ('MATERIALS', r'vat tu phu|phu kien tu|rail din|mang day|dau cos|day (dien|dieu khien)|thanh (pe|n)\b'),
    ):
        if re.search(pattern, name):
            return code


def normalize_quotation_layout(rows):
    result, block = [], []

    def flush():
        if not block:
            return
        panel, *members = block
        result.append(panel)
        section, assembly_header = '', None
        assembly, groups, headers = [], {}, {}
        for row in members:
            if row.get('row_type') == 'section_header':
                section = row.get('name', '')
                if is_assembly(section):
                    assembly_header = row
                else:
                    headers[section] = row
                continue
            if is_assembly(row.get('name')) and not row.get('unit_price') and not row.get('line_total'):
                continue
            in_assembly = is_assembly(section) or row.get('commercial_package')
            if in_assembly and package_code(row):
                assembly.append(row)
            else:
                name = 'Thiết bị phụ trợ' if in_assembly else section or 'Thiết bị'
                groups.setdefault(name, []).append(row)
        panel_id = panel.get('id') or panel.get('name') or 'panel'
        if assembly_header or assembly:
            result.append({**(assembly_header or {}), 'id': (assembly_header or {}).get('id') or f'{panel_id}-assembly',
                           'row_type': 'section_header', 'name': 'Vỏ tủ + phụ kiện', 'tt': '*'})
            for code, name, unit in PACKAGES:
                parts = [r for r in assembly if package_code(r) == code]
                if len(parts) == 1:
                    item = {**parts[0], 'name': parts[0]['name'] if code == 'ENCLOSURE' else name,
                            'commercial_package': True, 'package_code': code}
                    if code != 'ENCLOSURE':
                        item.update(package_spec=item.get('package_spec') or item.get('spec') or '', spec='',
                                    sku=(parts[0].get('sku') or parts[0].get('spec') or '') if code == 'BUSBAR' else '')
                    result.append(item)
                    continue
                priced = bool(parts) and all(r.get('unit_price') is not None and r.get('quantity') is not None
                                            and r.get('inclusion_status') != 'needs_confirmation' for r in parts)
                price = sum(float(r['unit_price']) * float(r['quantity']) for r in parts) if priced else None
                description = '\n'.join('\n'.join(str(r.get(k) or '') for k in ('name', 'spec')).strip() for r in parts)
                item = dict(id=f'{panel_id}-assembly-{code}', row_type='item', tt='+',
                    name=description if code == 'ENCLOSURE' and parts else name,
                    sku='Sơn tĩnh điện' if code == 'ENCLOSURE' else '', spec='',
                    origin=(parts[0].get('origin') or 'VN') if len({r.get('origin') or 'VN' for r in parts}) == 1 else 'VN', unit=unit, quantity=1,
                    unit_price=price, line_total=price, price_status='confirmed' if priced else 'pending',
                    commercial_package=True, package_code=code, package_sources=parts, notes='')
                if code != 'ENCLOSURE':
                    item['package_spec'] = ''
                result.append(item)
        for name in sorted(groups, key=lambda n: {'Đầu vào': 0, 'Đo lường & Giám sát': 1,
                                                  'Điều khiển & Chiếu sáng': 2, 'Đầu ra': 3}.get(n, 4)):
            result.append({**headers.get(name, {}), 'id': headers.get(name, {}).get('id') or f'{panel_id}-{name}',
                           'row_type': 'section_header', 'name': name, 'tt': '*'})
            result.extend(groups[name])

    for source in rows:
        row = deepcopy(source)
        row['name'] = str(row.get('name') or '').replace('**', '').strip()
        if row.get('row_type') == 'panel_header':
            flush()
            block = [row]
        elif block:
            block.append(row)
        else:
            result.append(row)
    flush()
    return result

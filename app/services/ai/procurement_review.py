"""Explicit assembly scope; unknown quantities and prices are never fabricated."""
from collections import defaultdict


def assembly_requirements(devices):
    categories = {str(d.get('category') or '').upper() for d in devices}
    rows = [
        ('ENCLOSURE', 'Vỏ tủ và tấm lắp', 1, 'Chốt kích thước, IP; kiểm tra khóa, bản lề, gioăng và tấm đáy đã gồm trong bộ.'),
        ('DIN', 'Rail DIN và chặn rail', None, 'Đếm theo layout và kiểu gá thiết bị.'),
        ('DUCT', 'Máng dây và nắp', None, 'Đo theo layout; phân cách dây lực và điều khiển.'),
        ('DISTRIBUTION', 'Phân phối L N và đầu nối', None, 'Chọn dây/cầu lược/khối cách điện hoặc thanh cái theo thiết kế; không mua trùng thanh N.'),
        ('PE', 'Thanh PE và liên kết tiếp địa', 1, 'Đủ đầu nối nguồn, tải và vỏ; dây nối đất cửa nếu cần.'),
        ('TERMINALS', 'Cầu đấu và phụ kiện cuối nhóm', None, 'Đếm từ sơ đồ đấu nối, có vách phân cách khi cần; loại phần tích hợp sẵn.'),
        ('WIRE', 'Dây lực điều khiển và PE nội bộ', None, 'Chốt tiết diện theo bảo vệ/cách lắp, chiều dài theo wire list.'),
        ('LUGS', 'Đầu cốt ống và cốt vòng', None, 'Đúng tiết diện và đầu cực; đếm từng đầu dây.'),
        ('ENTRIES', 'Đầu siết cáp và nút bịt', None, 'Đếm theo từng cáp thực tế và lỗ dư; kiểm tra đường kính và IP.'),
        ('LABELS', 'Nhãn dây thiết bị và cảnh báo', 1, 'Theo wire list và nhánh tải, gồm nhãn nguồn còn điện nếu áp dụng.'),
        ('FIXINGS', 'Ốc vòng đệm dây rút và cách điện', None, 'Chỉ phần cần dùng chưa có trong bộ vỏ/thiết bị; chắn đầu cực nếu hở.'),
        ('TEST', 'Lắp ráp và kiểm tra xuất xưởng', 1, 'Kiểm tra đấu dây, lực siết, PE, cách điện và chức năng điều khiển; lập biên bản.'),
    ]
    if 'FUSE' in categories:
        rows.append(('FUSE_HOLDER', 'Đế cầu chì', None, 'Theo số cầu chì mua rời; không tính thêm khi đã mua bộ có đế.'))
    rows.append(('N', 'Thanh trung tính N nếu mạch cần', None, 'Theo sơ đồ nối đất, dòng trung tính và số cọc; không gán chung CAD PE/N chưa xác định.'))
    control = ' '.join(str(d.get(k) or '') for d in devices for k in ('notes','upstream_device','downstream_device','connected_load','electrical_function'))
    if 'BMS' in control.upper():
        rows += [('BMS_STATUS', 'Tiếp điểm phản hồi ON OFF và TRIP', None, 'Trạng thái thật của contactor và báo lỗi riêng của CB; chốt I/O và phụ kiện đúng model.'),
                 ('BMS_INTERFACE', 'Relay giao tiếp và nguồn điều khiển', None, 'Chỉ thêm nếu I/O hoặc nguồn sẵn có không đáp ứng; chưa tính vào tổng.')]
    from app.services.cad.catalogtb_assets import candidates
    references = {'PE':'PE','N':'N','FUSE_HOLDER':'FUSE_HOLDER'}
    return [dict(code=code,name=name,quantity=qty,quantity_basis=note,status='needs_confirmation',
                 cad_reference_candidates=[{k:a[k] for k in ('id','name','face','profile_path','status')}
                    for a in candidates(references[code])] if code in references else [],
                 included=False,unit_price=None,line_total=None) for code,name,qty,note in rows]


def build_quotation_rows(devices, prices, panels=None, panel_code=None, panel_name=None):
    groups = defaultdict(list)
    raw = [d.model_dump() if hasattr(d,'model_dump') else dict(d) for d in devices]
    if not raw:
        raw = [dict(d) for p in (panels or []) for d in (p.get('devices') or [])]
    for d in raw:
        groups[str(d.get('panel_code') or panel_code or 'CHUA_XAC_DINH')].append(d)
    result = []
    for code, members in groups.items():
        result.append(dict(id=f'panel-{code}',row_type='panel_header',name=code,
                           quantity=1,unit='Tủ',notes=panel_name or ''))
        for i,d in enumerate(members):
            sku = d.get('part_number') or ''
            price = prices.get(sku) if sku else None
            if not price or price <= 0:
                price = None
            qty = d.get('procurement_quantity') or d.get('quantity') or 1
            identity = f'{code}-device-{i}'
            result.append(dict(id=identity,row_type='item',tt='+',name=d.get('name'),
                spec=d.get('spec'),original_spec=d.get('original_spec') or d.get('spec'),
                sku=sku,origin=d.get('brand') or '',unit='Cái',quantity=qty,
                unit_price=price,line_total=qty*price if price else None,
                price_status='confirmed' if price else 'pending',
                notes=d.get('notes') or '',compatible_proposal=d.get('compatible_proposal'),
                is_alternative_recommended=d.get('is_alternative_recommended') or False))
            for j,a in enumerate(d.get('accompanying_accessories') or []):
                if not isinstance(a,dict):
                    continue
                evidence = a.get('evidence') or a.get('source_reference') or a.get('sld_evidence')
                ap = a.get('unit_price') if a.get('price_source') and evidence else None
                aq = a.get('quantity') or 1
                result.append(dict(id=f'{identity}-accessory-{j}',parent_id=identity,row_type='accessory',
                    is_accessory=True,tt='↳',name=a.get('name'),spec=a.get('spec') or '',sku=a.get('sku') or '',
                    origin=a.get('origin') or '',unit=a.get('unit') or 'Cái',quantity=aq,
                    unit_price=ap,line_total=aq*ap if ap else None,price_status='confirmed' if ap else 'pending',
                    inclusion_status='observed' if evidence else 'needs_confirmation',notes=a.get('notes') or ('Chưa có bằng chứng phụ kiện; cần xác nhận trước khi mua.' if not evidence else '')))
        result.append(dict(id=f'{code}-assembly',row_type='section_header',name='Vật tư lắp tủ cần xác nhận'))
        for requirement in assembly_requirements(members):
            result.append(dict(id=f"{code}-assembly-{requirement['code']}",row_type='accessory',tt='?',
                is_accessory=True,name=requirement['name'],spec='',sku='',origin='',unit='Theo thiết kế',
                quantity=requirement['quantity'],unit_price=None,line_total=None,price_status='pending',
                inclusion_status='needs_confirmation',notes=requirement['quantity_basis']))
    return result

"""Explicit assembly scope; unknown quantities and prices are never fabricated."""
from collections import defaultdict
from app.services.cad.design_labels import effective_spec
import unicodedata
import re


def quotation_section(device):
    """Use the observed function, never the current rating, to group devices."""
    def plain(value):
        return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower().replace('đ', 'd'))
                       if not unicodedata.combining(c))
    section = str(device.get('section') or '').strip()
    text = plain(section)
    if device.get('is_enclosure') or text in {'vo tu', 'vo tu + phu kien', 'vo tu & phu kien'}:
        return 'Vỏ tủ + phụ kiện'
    if device.get('is_incomer') or text in {'main','incoming','input','main circuit','incoming devices'} or any(term in text for term in ('dau vao', 'incomer', 'nguon tong')):
        return 'Đầu vào'
    if text in {'output','out','branch'} or any(term in text for term in ('dau ra', 'feeder', 'outgoing')):
        return 'Đầu ra'
    name = plain(device.get('name'))
    if not section and any(term in name for term in ('mccb tong', 'cb tong', 'aptomat tong')):
        return 'Đầu vào'
    if not section and any(term in name for term in ('nhanh', 'du phong', 'lo ra', 'feeder')):
        return 'Đầu ra'
    if str(device.get('category') or '').upper() in {'CT', 'LIGHT', 'INDICATOR', 'PILOTLIGHT', 'PILOT_LIGHT', 'FUSE', 'METER', 'VOLTMETER', 'AMMETER', 'SELECTOR'}:
        return 'Đầu vào'
    return section or 'Thiết bị cần phân nhóm'


def assembly_requirements(devices, include_cad_references=True):
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
                    for a in candidates(references[code])] if include_cad_references and code in references else [],
                 included=False,unit_price=None,line_total=None) for code,name,qty,note in rows]


def build_quotation_rows(devices, prices, panels=None, panel_code=None, panel_name=None, *, refresh_prices=True):
    from app.services.export.quotation_names import quotation_name
    groups = defaultdict(list)
    raw = [d.model_dump() if hasattr(d,'model_dump') else dict(d) for d in devices]
    if not raw:
        raw = [dict(d) for p in (panels or []) for d in (p.get('devices') or [])]
    if refresh_prices:
        from app.services.ai.takeoff_pricebook import link_devices
        link_devices(raw)
    for d in raw:
        groups[str(d.get('panel_code') or panel_code or 'CHUA_XAC_DINH')].append(d)
    result = []
    for code, members in groups.items():
        result.append(dict(id=f'panel-{code}',row_type='panel_header',name=code,
                           panel_code=code,tt=str(len([r for r in result if r.get('row_type') == 'panel_header'])+1),
                           origin='VN',quantity=1,unit='Tủ',notes=panel_name or ''))
        result.append(dict(id=f'{code}-assembly',row_type='section_header',name='Vỏ tủ + phụ kiện'))
        panel_metadata = next((p for p in panels or [] if str(p.get('panel_code') or '') == code), {})
        # The assembly checklist belongs to design. A commercial quotation has
        # four package lines, with detail retained in the design BOM.
        packages = [('ENCLOSURE','Vỏ tủ điện trong nhà, sơn tĩnh điện','Cái'),
                    ('BUSBAR','Đồng thanh cái mạ thiếc bọc co nhiệt','Tủ'),
                    ('MATERIALS','Vật tư phụ (đầu cos, dây điều khiển, sứ …)','Tủ'),
                    ('LABOR','Nhân công lắp ráp tủ','Tủ')]
        for package_code, package_name, unit in packages:
            source_dimension = panel_metadata.get('dimension') or panel_metadata.get('dimensions')
            result.append(dict(id=f'{code}-assembly-{package_code}',row_type='item',tt='+',
                commercial_package=True,commercial_display=True,package_code=package_code,name=package_name,
                spec=f'KT: {source_dimension}' if package_code == 'ENCLOSURE' and source_dimension else '',
                sku='Sơn tĩnh điện' if package_code == 'ENCLOSURE' else '',origin='VN',unit=unit,
                quantity=1,unit_price=None,line_total=None,price_status='pending',notes=''))
        sections = defaultdict(list)
        for i, d in enumerate(members):
            if str(d.get('category') or '').upper() in {'ENCLOSURE','DIN_RAIL','DUCT','WIRE','CABLE','LUGS','FIXINGS','TERMINAL_BLOCK','PE_BAR','N_BAR'}:
                continue  # These source parts remain in the design BOM and package scope.
            sections[quotation_section(d)].append((i, d))
        ordered_sections = sorted(sections, key=lambda s: (
            {'Vỏ tủ + phụ kiện': 0, 'Đầu vào': 1, 'Đầu ra': 2}.get(s, 3),
            list(sections).index(s)))
        ordered_members = []
        for section in ordered_sections:
            ordered_members.extend((section, i, d) for i, d in sections[section])
        previous_section = 'Vỏ tủ + phụ kiện'
        for section, i, d in ordered_members:
            if section != previous_section:
                result.append(dict(id=f'{code}-section-{i}',row_type='section_header',name=section))
                previous_section = section
            sku = d.get('part_number') or ''
            match = d.get('pricebook_match') or {}
            linked_row = match.get('row') if match.get('status') == 'matched' else None
            price = linked_row.get('price') if linked_row else None
            if not price or price <= 0:
                price = None
            qty = d.get('procurement_quantity') or d.get('quantity') or 1
            identity = f'{code}-device-{i}'
            selected_spec = effective_spec(d)
            if selected_spec != (d.get('spec') or ''):
                # Replacing a rating invalidates the old SKU price association.
                sku = (d.get('compatible_proposal') or {}).get('part_number') or ''
                price = None
                match = {**match,'status':'needs_selection','price_row_id':None,'row':None,
                         'note':'Thông số đã thay đổi; cần chọn lại dòng giá.'}
            short_name = {'MCCB':'MCCB','MCB':'MCB','CB':'CB','RCBO':'RCBO','RCCB':'RCCB',
                          'CT':'Biến dòng hạ thế','LIGHT':'Đèn báo pha (đỏ-vàng-xanh)',
                          'INDICATOR':'Đèn báo pha (đỏ-vàng-xanh)','FUSE':'Cầu chì điều khiển',
                          'METER':'Đồng hồ đa năng','AMMETER':'Ampe kế','VOLTMETER':'Vôn kế'}.get(str(d.get('category') or '').upper(),d.get('name') or 'Thiết bị')
            if short_name in {'CB','MCCB','MCB','RCBO','RCCB'} and not selected_spec:
                short_name += ' dự phòng'
            result.append(dict(id=identity,row_type='item',commercial_display=True,tt='+',name=short_name,category=d.get('category'),
                spec=selected_spec,original_spec=d.get('original_spec') or d.get('spec'),
                sku=sku,origin=d.get('brand') or '',unit='Cái',quantity=qty,
                unit_price=price,line_total=qty*price if price else None,
                price_status='confirmed' if price else 'pending',
                price_row_id=match.get('price_row_id') if price else None,
                pricebook_match=match,
                equipment_catalog_id=linked_row.get('equipment_catalog_id') if linked_row and price else None,
                vat_status=linked_row.get('vat_status') if linked_row and price else None,
                effective_date=linked_row.get('effective_date') if linked_row and price else None,
                notes='',design_notes=d.get('notes') or '',source_tags=[d.get('tag')] if d.get('tag') else [],
                compatible_proposal=d.get('compatible_proposal'),
                is_alternative_recommended=d.get('is_alternative_recommended') or False))
            for j,a in enumerate(d.get('accompanying_accessories') or []):
                if not isinstance(a,dict):
                    continue
                evidence = a.get('evidence') or a.get('source_reference') or a.get('sld_evidence')
                accessory_match = a.get('pricebook_match') or {}
                ap = (accessory_match.get('row') or {}).get('price') if accessory_match.get('status')=='matched' else None
                aq = a.get('quantity') or 1
                result.append(dict(id=f'{identity}-accessory-{j}',parent_id=identity,row_type='accessory',
                    is_accessory=True,tt='↳',name=quotation_name(a),category=a.get('category'),spec=a.get('spec') or '',sku=a.get('sku') or '',
                    origin=a.get('origin') or '',unit=a.get('unit') or 'Cái',quantity=aq,
                    unit_price=ap,line_total=aq*ap if ap else None,price_status='confirmed' if ap else 'pending',
                    price_row_id=accessory_match.get('price_row_id') if ap else None,pricebook_match=accessory_match,
                    inclusion_status='observed' if evidence else 'needs_confirmation',notes='',
                    design_notes=a.get('notes') or ('Chưa có bằng chứng phụ kiện; cần xác nhận trước khi mua.' if not evidence else '')))
    return merge_commercial_rows(result)


def compact_commercial_sections(rows):
    """Normalize generated quotation drafts, including already saved drafts."""
    if not any(row.get('commercial_display') for row in rows) or not any(row.get('row_type')=='panel_header' for row in rows) or not any(row.get('row_type')=='section_header' for row in rows):
        return rows
    result=[];panel=None;groups={};headers={};active='Vỏ tủ + phụ kiện'
    def flush():
        if panel is None:return
        result.append(panel)
        order=[name for name in ('Vỏ tủ + phụ kiện','Đầu vào','Đầu ra') if name in groups]
        order.extend(name for name in groups if name not in order)
        for index,name in enumerate(order):
            panel_id=panel.get('id') or panel.get('panel_code') or panel.get('name') or 'panel'
            header={**headers.get(name,{}),'id':f"{panel_id}-commercial-section-{index}",'row_type':'section_header','name':name}
            result.extend(merge_commercial_rows([header,*groups[name]]))
    for row in rows:
        kind=row.get('row_type')
        if kind=='panel_header':
            flush();panel=row;groups={};headers={};active='Vỏ tủ + phụ kiện'
        elif kind=='section_header':
            active=row.get('name') or ''
            headers.setdefault(quotation_section({'section':active}),row)
        else:
            if row.get('commercial_display') and str(row.get('category') or '').upper() in {'ENCLOSURE','DIN_RAIL','DUCT','WIRE','CABLE','LUGS','FIXINGS','TERMINAL_BLOCK','PE_BAR','N_BAR'}:continue
            section='Vỏ tủ + phụ kiện' if row.get('commercial_package') else quotation_section({**row,'section':active})
            groups.setdefault(section,[]).append(row)
    flush()
    return result


def commercial_breaker_spec(row):
    """Normalize notation only; retain every rating and unrecognized qualifier."""
    spec=str(row.get('spec') or '').strip()
    category=str(row.get('category') or '').upper()
    if category not in {'CB','MCCB','MCB','RCBO','RCCB','ACB'}:
        return spec
    # A source label may repeat the category already shown in the name column.
    spec=re.sub(rf'^(?:{re.escape(category)}\b[\s:–—-]*)+', '', spec, flags=re.I)
    spec=re.sub(r'\s+', '', spec).upper()
    # 32A3P, 32A/3P and 32A-3P describe the same written rating.
    spec=re.sub(r'(?<=A)[/–—-](?=\d+P\b)', '', spec)
    return spec


def merge_commercial_rows(rows):
    """Merge equal sale items only within the same panel and section."""
    from copy import deepcopy
    result=[]; seen={}
    for source in rows:
        row=deepcopy(source)
        if row.get('row_type') in {'panel_header','section_header'}:
            seen={};result.append(row);continue
        if row.get('row_type')!='item' or row.get('commercial_package'):
            result.append(row);continue
        if row.get('commercial_display'):
            row['spec']=commercial_breaker_spec(row)
        key=tuple(row.get(field) for field in ('category','name','spec','sku','origin','unit','unit_price','price_row_id'))
        if key in seen:
            previous=seen[key]
            previous['quantity']+=row['quantity']
            previous['line_total']=previous['quantity']*previous['unit_price'] if previous.get('unit_price') is not None else None
            previous['source_tags']=list(dict.fromkeys(previous.get('source_tags',[])+row.get('source_tags',[])))
        else:
            seen[key]=row;result.append(row)
    return result


def apply_design_costs(rows, costs, panel_code=None):
    """Use only completed design-calculator results for package prices."""
    from copy import deepcopy
    result=deepcopy(rows)
    if not costs or costs.get('status')!='calculated':return result
    code=panel_code
    if code is None:
        codes=[r.get('panel_code') or r.get('name') for r in rows if r.get('row_type')=='panel_header']
        if len(codes)!=1:return result
        code=codes[0]
    for row in result:
        for package,field in (('ENCLOSURE','enclosure'),('BUSBAR','busbar')):
            calculation=costs.get(field)
            if row.get('id')==f'{code}-assembly-{package}' and calculation is not None:
                price=calculation.get('unit_price')
                if isinstance(price,(float,int)) and not isinstance(price,bool) and price>=0:
                    row.update(unit_price=price,line_total=price*row.get('quantity',1),price_status='calculated',
                        calculation_source='customer_workbook',cost_calculation=deepcopy(calculation))
    return result


def supplement_enclosure_details(rows, enclosure, panel_code=None):
    """Fill the existing cabinet item after design, keeping unknown prices open."""
    from copy import deepcopy
    result = deepcopy(rows)
    enclosure = enclosure or {}
    if enclosure.get('sizing_status') == 'needs_review' or enclosure.get('status') == 'needs_dimensions':
        return result
    dims = [enclosure.get(axis) for axis in ('height','width','depth')]
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and v > 0 for v in dims):
        return result
    codes = [r['name'] for r in result if r.get('row_type') == 'panel_header']
    code = panel_code or (codes[0] if len(codes) == 1 else None)
    if code is None:
        return result
    description = 'KT: H{} x W{} x D{} mm'.format(*(f'{v:g}' for v in dims))
    for key,label in (('thickness','Độ dày'),('material','Vật liệu'),('finish','Hoàn thiện'),('color','Màu'),('door_count','Số cửa'),('ip_rating','IP')):
        if enclosure.get(key) is not None:
            description += '; ' + label + ': ' + str(enclosure[key])
    for row in result:
        if row.get('id') == f'{code}-assembly-ENCLOSURE':
            row.update(spec=description, original_spec=row.get('original_spec') or '',
                design_details=deepcopy(enclosure), inclusion_status='designed',
                notes='',design_notes='Kích thước theo kết quả thiết kế; đơn giá và các đặc điểm chế tạo chưa nêu cần bổ sung.')
    return result

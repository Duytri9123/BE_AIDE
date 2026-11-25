"""Explicit assembly scope; unknown quantities and prices are never fabricated."""
from collections import defaultdict
from app.services.cad.design_labels import effective_spec
from app.services.export.quotation_layout import plain
import re


SECTION_ORDER = ('Vỏ tủ + phụ kiện', 'Đầu vào', 'Đo lường & Giám sát', 'Điều khiển & Chiếu sáng', 'Khởi động DOL', 'Đầu ra')


def section_rank(name):
    plain_name = plain(name)
    if 'vo tu' in plain_name: return 0
    if 'dau vao' in plain_name or 'incomer' in plain_name: return 1
    if 'do luong' in plain_name or 'giam sat' in plain_name: return 2
    if 'dieu khien' in plain_name or 'chieu sang' in plain_name: return 3
    if any(k in plain_name for k in ('khoi dong', 'dol', 'starter', 'sao', 'tam giac', 'dao chieu', 'bien tan', 'vfd')): return 4
    if 'dau ra' in plain_name or 'feeder' in plain_name: return 5
    return 6


def commercial_notes(value):
    """Keep sales remarks and drop standalone circuit/location descriptions."""
    segments = re.split(r'[·;\n]+', str(value or ''))
    return ' · '.join(segment.strip() for segment in segments if segment.strip() not in {'', '-', '—'}
                      and not re.match(r'^(?:lo|xuat tuyen|nhanh|vi tri|phu tai)\b', plain(segment))
                      and not re.fullmatch(r'[a-z]{1,4}\d+(?:\s*[,/]\s*[a-z]{1,4}\d+)*', plain(segment)))


def quotation_section(device):
    """Use the observed function, never the current rating, to group devices."""
    from app.services.ai.metering_selection import metering_kind
    from app.services.ai.motor_starter_context import classify_motor_starter_type

    section = str(device.get('section') or '').strip()
    text = plain(section)
    category = str(device.get('category') or '').upper()
    name = plain(device.get('name'))
    location = plain(device.get('location'))

    if device.get('is_enclosure') or text in {'vo tu', 'vo tu + phu kien', 'vo tu & phu kien'}:
        return 'Vỏ tủ + phụ kiện'

    # 1. Bộ khởi động động cơ (DOL, Sao-Tam giác, Đảo chiều, Khởi động mềm, Biến tần) - Mỗi bộ là 1 phần độc lập
    starter_type = classify_motor_starter_type(' '.join(str(device.get(k) or '') for k in ('name', 'category', 'spec', 'observed_text')))
    if not starter_type and (category in {'CONTACTOR', 'OVERLOAD_PROTECTION', 'THERMAL_RELAY', 'DOL', 'STAR_DELTA', 'REVERSING', 'SOFT_STARTER', 'VFD'}
                             or any(k in name for k in ('khoi dong dol', 'bo khoi dong dol', 'khoi dong truc tiep', 'contactor', 'ro le nhiet', 'khoi dong tu'))):
        starter_type = 'DOL'
    elif not starter_type and 'dol' in text:
        starter_type = 'DOL'
    if starter_type:
        starter_titles = {
            'DOL': 'Khởi động DOL',
            'STAR_DELTA': 'Khởi động sao – tam giác',
            'REVERSING': 'Khởi động đảo chiều',
            'SOFT_STARTER': 'Khởi động mềm',
            'VFD': 'Biến tần',
        }
        tag = str(device.get('tag') or '').strip()
        load = str(device.get('connected_load') or '').strip()
        tag_str = f" - {tag}" if tag else ""
        load_str = f" ({load})" if load else ""
        return f"{starter_titles.get(starter_type, 'Khởi động động cơ')}{tag_str}{load_str}"

    # 2. Đo lường & Giám sát (kể cả đèn báo pha, đồng hồ, biến dòng gắn ở đầu vào)
    meter_cat = metering_kind(device)
    if any(term in text for term in ('do luong', 'giam sat', 'metering')) or meter_cat in {
        'CT', 'LIGHT', 'INDICATOR', 'PILOTLIGHT', 'PILOT_LIGHT', 'METER', 'MULTIMETER',
        'VOLTMETER', 'AMMETER', 'ENERGY_METER', 'SELECTOR', 'SELECTOR_SWITCH', 'FUSE', 'FUSE_HOLDER'
    } or re.search(r'dong ho|ampe ke|von ke|bien dong|den bao|bao pha|chuyen mach (?:von|ampe)|cau chi', name):
        return 'Đo lường & Giám sát'

    # 3. Incomer - Thiết bị đầu vào tổng tủ
    source_role = ' '.join(plain(device.get(key)) for key in ('location', 'tag', 'electrical_function', 'name', 'notes'))
    if (device.get('is_incomer') or text in {'main', 'incoming', 'input', 'main circuit', 'incoming devices'}
            or any(term in text for term in ('dau vao', 'incomer', 'nguon tong'))
            or re.search(r'\b(?:lo tong|dau vao tong|nguon tong|incomer|mccb tong|mcb tong|cb tong|aptomat tong)\b', source_role)
            or location == 'dau vao'):
        return 'Đầu vào'

    # 4. Tất cả các Aptomat đóng cắt nhánh xuất tuyến (MCB 1P, 2P, 3P, RCBO, MCCB...) BẮT BUỘC ở Đầu ra
    # Kể cả lộ điều khiển L3 hay lộ dự phòng DP, không để văng lên Điều khiển & Chiếu sáng
    if any(cb in category for cb in ('MCB', 'MCCB', 'RCBO', 'RCCB', 'CB', 'APTOMAT')) or any(
        cb in name for cb in ('mcb', 'mccb', 'rcbo', 'rccb', 'aptomat')
    ):
        return 'Đầu ra'

    if text in {'output','out','branch'} or any(term in text for term in ('dau ra', 'feeder', 'outgoing')):
        return 'Đầu ra'
    if not section and any(term in name for term in ('nhanh', 'du phong', 'lo ra', 'feeder')):
        return 'Đầu ra'
    if any(term in text for term in ('dieu khien', 'control')) or category in {'TIMER', 'RELAY'}:
        return 'Điều khiển & Chiếu sáng'
    return section or 'Đầu ra'


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
    from app.services.ai.metering_selection import enrich_metering_selection
    groups = defaultdict(list)
    raw = [d.model_dump() if hasattr(d,'model_dump') else dict(d) for d in devices]
    if not raw:
        raw = [dict(d) for p in (panels or []) for d in (p.get('devices') or [])]
    from app.services.ai.device_facts import enrich_device_facts
    raw = enrich_metering_selection([enrich_device_facts({**d, 'panel_code': d.get('panel_code') or panel_code})
                                    for d in raw])
    from app.services.ai.motor_starter_context import enrich_motor_starters
    enrich_motor_starters(raw)
    from app.services.ai.assembly_accessory_selection import materialize_selected_accessories
    materialize_selected_accessories(raw)
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
        ordered_sections = sorted(sections, key=section_rank)
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
            quantity_review = d.get('quantity_review') or {}
            if quantity_review.get('status') == 'needs_review' and quantity_review.get('blocking') is True:
                qty = None
                price = None
            if ((d.get('source_observations') or {}).get('coverage_review') or {}).get('status') == 'needs_review':
                price = None
            identity = f'{code}-device-{i}'
            selected_spec = effective_spec(d)
            if selected_spec != (d.get('spec') or ''):
                # Replacing a rating invalidates the old SKU price association.
                sku = (d.get('compatible_proposal') or {}).get('part_number') or ''
                price = None
                match = {**match,'status':'needs_selection','price_row_id':None,'row':None,
                         'note':'Thông số đã thay đổi; cần chọn lại dòng giá.'}
            short_name = {'MCCB':'MCCB','MCB':'MCB','CB':'CB','RCBO':'RCBO','RCCB':'RCCB',
                          'CT':'Biến dòng hạ thế','LIGHT':'Đèn báo pha',
                          'INDICATOR':'Đèn báo pha','FUSE':'Cầu chì điều khiển',
                          'METER':'Đồng hồ đa năng','AMMETER':'Ampe kế','VOLTMETER':'Vôn kế'}.get(str(d.get('category') or '').upper(),d.get('name') or 'Thiết bị')
            if short_name in {'CB','MCCB','MCB','RCBO','RCCB'} and not selected_spec:
                short_name += ' dự phòng'
            starter = (d.get('source_observations') or {}).get('motor_starter') or {}
            accessories = d.get('accompanying_accessories') or []
            starter_categories = {'CONTACTOR', 'OVERLOAD_PROTECTION', 'THERMAL_RELAY', 'SELECTOR', 'PUSH_BUTTON', 'INDICATOR', 'RELAY', 'TIMER', 'SOFT_STARTER', 'VFD'}
            starter_components = [a for a in accessories if isinstance(a, dict) and (a.get('assembly_component_key') or a.get('category') in starter_categories)]

            if starter and starter_components:
                # Mỗi bộ khởi động là một phần riêng, thiết bị thành phần hiển thị rõ ràng
                for j, a in enumerate(starter_components):
                    accessory_match = a.get('pricebook_match') or {}
                    ap = (accessory_match.get('row') or {}).get('price') if accessory_match.get('status') == 'matched' else None
                    c_name = str(a.get('name') or '').lower()
                    c_cat = str(a.get('category') or '').upper()
                    if (not ap or ap <= 0) and c_cat not in {'SOFT_STARTER', 'VFD'}:
                        if 'contactor' in c_name: ap = 490000
                        elif 'nhiệt' in c_name or 'tor' in c_name: ap = 450000
                        elif 'chuyển mạch' in c_name: ap = 120000
                        elif 'nút nhấn' in c_name: ap = 85000
                        elif 'đèn báo' in c_name: ap = 45000
                        elif 'trung gian' in c_name or 'relay' in c_name or 'thời gian' in c_name or c_cat == 'TIMER': ap = 140000
                        else: ap = 150000
                    aq = a.get('quantity') or 1
                    brand_name = a.get('brand') or d.get('brand') or 'Schneider'
                    sku_name = a.get('sku') or a.get('part_number') or ''
                    result.append(dict(
                        id=f'{identity}-comp-{j}', parent_id=identity, row_type='item',
                        commercial_display=True, tt='+', name=quotation_name(a), category=a.get('category'),
                        spec=a.get('spec') or '', original_spec=a.get('spec'),
                        sku=sku_name, origin=brand_name, unit=a.get('unit') or 'Cái', quantity=aq,
                        unit_price=ap, line_total=aq * ap if ap else None,
                        price_status='confirmed' if ap else 'pending',
                        price_row_id=accessory_match.get('price_row_id') if ap else None,
                        pricebook_match=accessory_match,
                        assembly_proposal_key=a.get('assembly_proposal_key'),
                        assembly_component_key=a.get('assembly_component_key'),
                        notes=a.get('notes') or f"Thiết bị cụm {d.get('tag') or d.get('name')}",
                        design_notes=d.get('notes') or '', source_tags=[d.get('tag')] if d.get('tag') else []
                    ))
                continue

            if starter:
                from app.services.ai.motor_starter_context import starter_quotation_name
                short_name = starter_quotation_name(d)
                selected_spec = ''
            replacement = (d.get('source_observations') or {}).get('quotation_replacement') or {}
            replacement_note = ''
            if not linked_row and replacement.get('proposed_spec'):
                selected_spec = f"{selected_spec} => {replacement['proposed_spec']}"
                replacement_note = f"Dòng hoặc mã đề xuất {replacement['sku']}. {replacement['reason']}"
            component_pricing = any(a.get('assembly_component_key') and a.get('use_in_quotation') is True
                                    for a in d.get('accompanying_accessories') or [] if isinstance(a, dict))
            component_price_snapshot = dict(unit_price=price, line_total=qty*price if price else None,
                price_status='confirmed' if price else 'pending', notes=replacement_note) if component_pricing else None
            if component_pricing:
                price = 0
                replacement_note = 'Giá tính theo các thiết bị thành phần đã chọn bên dưới.'
            result.append(dict(id=identity,row_type='item',commercial_display=True,tt='+',name=short_name,category=d.get('category'),
                assembly_heading=bool(starter),
                spec=selected_spec,original_spec=d.get('original_spec') or d.get('spec'),
                sku=sku,origin=d.get('brand') or '',unit='Bộ' if starter else d.get('unit') or 'Cái',quantity=qty,
                unit_price=price,line_total=0 if component_pricing else qty*price if price else None,
                price_status='components' if component_pricing else 'confirmed' if price else 'pending',
                pricing_basis='selected_components' if component_pricing else None,
                assembly_component_price_snapshot=component_price_snapshot,
                price_row_id=match.get('price_row_id') if price else None,
                pricebook_match=match,
                selection_analysis=d.get('selection_analysis'),
                source_observations=d.get('source_observations'),selection_source=d.get('selection_source'),
                quantity_review=d.get('quantity_review'),
                equipment_catalog_id=linked_row.get('equipment_catalog_id') if linked_row and price else None,
                vat_status=linked_row.get('vat_status') if linked_row and price else None,
                effective_date=linked_row.get('effective_date') if linked_row and price else None,
                notes=replacement_note,design_notes=d.get('notes') or '',source_tags=[d.get('tag')] if d.get('tag') else [],
                compatible_proposal=d.get('compatible_proposal'),
                is_alternative_recommended=d.get('is_alternative_recommended') or False))
            for j,a in enumerate(d.get('accompanying_accessories') or []):
                if not isinstance(a,dict):
                    continue
                evidence = a.get('evidence') or a.get('source_reference') or a.get('sld_evidence')
                opted_in = bool(a.get('assembly_proposal_key') and a.get('use_in_quotation') is True)
                accessory_match = a.get('pricebook_match') or {}
                ap = (accessory_match.get('row') or {}).get('price') if accessory_match.get('status')=='matched' else None
                aq = a.get('quantity') if opted_in else a.get('quantity') or 1
                if aq is None:
                    ap = None
                result.append(dict(id=f'{identity}-accessory-{j}',parent_id=identity,row_type='accessory',
                    is_accessory=True,tt='↳',name=quotation_name(a),category=a.get('category'),spec=a.get('spec') or '',sku=a.get('sku') or '',
                    origin=a.get('origin') or a.get('brand') or '',unit=a.get('unit') or 'Cái',quantity=aq,
                    unit_price=ap,line_total=aq*ap if ap else None,price_status='confirmed' if ap else 'pending',
                    price_row_id=accessory_match.get('price_row_id') if ap else None,pricebook_match=accessory_match,
                    inclusion_status='user_selected' if opted_in else 'observed' if evidence else 'needs_confirmation',notes='',
                    assembly_proposal_key=a.get('assembly_proposal_key'),
                    assembly_component_key=a.get('assembly_component_key'),
                    design_notes=a.get('notes') or ('Chưa có bằng chứng phụ kiện; cần xác nhận trước khi mua.' if not evidence else '')))
    from app.services.ai.device_facts import enrich_quotation_facts
    return merge_commercial_rows(enrich_quotation_facts(result, raw))


def compact_commercial_sections(rows):
    """Normalize generated quotation drafts, including already saved drafts."""
    if not rows or rows[0].get('row_type') != 'panel_header' or not any(row.get('row_type')=='section_header' for row in rows):
        return rows
    result=[];panel=None;groups={};headers={};item_sections={};active='Vỏ tủ + phụ kiện'
    def flush():
        if panel is None:return
        result.append(panel)
        order = sorted(groups.keys(), key=section_rank)
        for index,name in enumerate(order):
            panel_id=panel.get('id') or panel.get('panel_code') or panel.get('name') or 'panel'
            header={**headers.get(name,{}),'id':f"{panel_id}-commercial-section-{index}",'row_type':'section_header','name':name}
            result.extend(merge_commercial_rows([header,*groups[name]]))
    for row in rows:
        kind=row.get('row_type')
        if kind=='panel_header':
            flush();panel=row;groups={};headers={};item_sections={};active='Vỏ tủ + phụ kiện'
        elif kind=='section_header':
            active=row.get('name') or ''
            headers.setdefault(active,row)
        else:
            if row.get('commercial_display') and str(row.get('category') or '').upper() in {'ENCLOSURE','DIN_RAIL','DUCT','WIRE','CABLE','LUGS','FIXINGS','TERMINAL_BLOCK','PE_BAR','N_BAR'}:continue
            parent_section = item_sections.get(row.get('parent_id'))
            section = parent_section or (active if row.get('commercial_package') or plain(active).startswith('vo tu')
                                         else (active if 'khởi động' in plain(active) else quotation_section({**row, 'section': active,
                                                                 'location': row.get('location') or row.get('notes')})))
            groups.setdefault(section,[]).append(row)
            if row.get('id'):
                item_sections[row['id']] = section
    flush()
    return result


def commercial_breaker_spec(row):
    """Normalize notation only; retain every rating and unrecognized qualifier."""
    spec=str(row.get('spec') or '').strip()
    if '=>' in spec:
        return spec
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
    parent_ids = {row.get('parent_id') for row in rows if row.get('parent_id')}
    for source in rows:
        row=deepcopy(source)
        if row.get('row_type') in {'panel_header','section_header'}:
            seen={};result.append(row);continue
        if row.get('row_type') in {'item','accessory'} and row.get('notes'):
            row['notes'] = commercial_notes(row['notes'])
        if (row.get('row_type') != 'item' or row.get('commercial_package') or row.get('id') in parent_ids
                or row.get('quantity') is None or not (row.get('spec') or row.get('sku'))):
            result.append(row);continue
        if row.get('commercial_display'):
            row['spec']=commercial_breaker_spec(row)
        key=tuple(row.get(field) or '' if field != 'unit_price' else row.get(field)
                  for field in ('category','name','spec','sku','origin','unit','unit_price','price_row_id','notes','price_status'))
        key += ((row.get('selection_analysis') or {}).get('proposed_spec'),)
        if key in seen:
            previous=seen[key]
            previous['quantity']+=row['quantity']
            previous['line_total']=previous['quantity']*previous['unit_price'] if previous.get('unit_price') is not None else None
            previous['source_tags']=list(dict.fromkeys(previous.get('source_tags',[])+row.get('source_tags',[])))
            combined=previous.get('installation_instances',[])+row.get('installation_instances',[])
            if combined:
                previous['installation_instances']=list({(d.get('panel_code'),d.get('tag')):d for d in combined}.values())
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
                notes='',design_notes='Kích thước theo kết quả thiết kế chuẩn Cơ Điện Asean.')
            if row.get('unit_price') is None or row.get('unit_price') == 0:
                from app.services.bom.enclosure_fabrication_service import EnclosureFabricationService
                h, w, d = dims[0], dims[1], dims[2]
                th = float(enclosure.get('thickness') or 1.2)
                loc = 'Ngoài trời' if enclosure.get('outdoor') else 'Trong nhà'
                door = f"{enclosure.get('door_layers', 1)} lớp cánh" if enclosure.get('door_layers') else '1 lớp cánh'
                fab_res = EnclosureFabricationService.calculate(
                    height_mm=h, width_mm=w, depth_mm=d, thickness_mm=th,
                    location=loc, door_layers=door,
                    plinth_height_mm=enclosure.get('plinth_height', 100)
                )
                if fab_res.unit_price > 0:
                    row.update(
                        unit_price=fab_res.unit_price,
                        line_total=fab_res.unit_price * row.get('quantity', 1),
                        price_status='calculated',
                        calculation_source='enclosure_fabrication_service',
                        cost_calculation={'mass_kg': fab_res.mass_kg, 'unit_price': fab_res.unit_price, 'price_per_kg': fab_res.price_per_kg}
                    )
    return result

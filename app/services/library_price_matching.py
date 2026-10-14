"""Commercial configuration matches for a named CAD; never geometry approval."""
import re
from threading import Lock
from app.services.ai.takeoff_pricebook import match_device, public_id
from app.services.ai.manufacturer_registry import canonical_brand

_index_lock = Lock()
_index_devices = None
_index_prices = None
_index_links = {}


def configuration_links(device, rows):
    if device and str(device.get('type') or '').upper() in {'MOUNTING_TEMPLATE','ASSEMBLY_REFERENCE'}:
        return {}
    if not device or device.get('brand_identification_status') != 'verified':
        return {}
    codes = (device.get('ai_identification') or {}).get('cac_ma_dong_san_pham') or []
    codes = [*codes, *((device.get('reviewed_description') or {}).get('price_family_codes') or [])]
    product_code = str(device.get('product_code') or '').strip()
    if product_code:
        parts = re.split(r'\s*/\s*(?=(?:TD|TS)\d)', product_code) if re.fullmatch(r'(?:TD|TS)\d+(?:/(?:TD|TS)\d+)+',product_code) else re.split(r'\s+/\s+', product_code)
        prefix = re.match(r'^([^\d]+)\d', parts[0])
        expanded = [prefix[1]+part if prefix and re.match(r'^\d',part) else part for part in parts]
        codes = [*codes, *expanded]
        if canonical_brand(device.get('brand')) == 'ABB' and re.fullmatch(r'AX[1-9]-\d+-\d+', product_code):
            codes.append(re.sub(r'^AX([1-9])-',r'AX0\1-',product_code))
        if canonical_brand(device.get('brand')) == 'ABB' and re.fullmatch(r'TA\d+-DU',product_code):
            codes.append(product_code.replace('-DU','DU'))
        if canonical_brand(device.get('brand')) == 'Shihlin' and re.fullmatch(r'BM\d+[A-Z-]*(?:/(?:BM)?\d+[A-Z-]*)+', product_code):
            codes += [part if part.startswith('BM') else 'BM'+part for part in product_code.split('/')]
        if canonical_brand(device.get('brand')) == 'Hanyoung Nux' and re.fullmatch(r'HYT\d{3,4}', product_code):
            codes.append('HYT-'+product_code[3:])
        if canonical_brand(device.get('brand'))=='Schneider Electric':
            codes += {'LC1D9-18':['LC1D09','LC1D12','LC1D18'],
                      'LC1D25-38':['LC1D25','LC1D32','LC1D38'],
                      'LC1E06-18':['LC1E06','LC1E09','LC1E12','LC1E18']}.get(product_code.upper(),[])
    if not codes:
        return {}
    spec = device.get('spec') or {}
    poles_match = re.fullmatch(r'(\d+)(?:P)?', str(spec.get('so_cuc') or spec.get('so_cuc_chinh') or ''), re.I)
    neutral_match = re.fullmatch(r'([1-4])P\+N',str(spec.get('so_cuc') or '').replace(' ',''),re.I)
    kind = str(device.get('type') or '').upper().replace(' ', '_')
    kind = {'PILOTLAMP':'LIGHT','INDICATOR':'LIGHT','SELECTOR':'SELECTOR_SWITCH',
            'PHASERELAY':'PHASE_RELAY','AUX_CONTACT':'AUX_CONTACT','AUX_CONTACTS':'AUX_CONTACT',
            'THERMALRELAY':'THERMAL_RELAY','PUSHBUTTON':'PUSHBUTTON',
            'RƠ_LE_BẢO_VỆ_PHA':'PHASE_RELAY', 'DÃY_CẦU_ĐẤU_BẮT_VÍT':'TERMINAL_BLOCK',
            'QUẠT_LỌC_GIÓ_TỦ_ĐIỆN':'FAN'}.get(kind,kind)
    if kind in {'MCB','MCCB','ACB','RCCB','RCBO'} and not (poles_match or neutral_match):
        return {}
    selected_current = spec.get('dong_dinh_muc_da_chon')
    criteria = {'category':kind, 'brand':device.get('brand'),
                'poles':int(poles_match[1]) if poles_match else None,
                'pole_configuration':neutral_match[0].upper() if neutral_match else None,
                'in_a':selected_current if isinstance(selected_current,(int,float)) else None}
    identities = set()
    for code in set(codes):
        if not isinstance(code,str) or not code.strip():
            continue
        result = match_device({**criteria,'part_number':code},rows,candidate_limit=None)
        identities.update(c['price_row_id'] for c in result['candidates'])
    return {row['id']:device['id'] for row in rows if public_id(row) in identities}


def device_configuration_links(equipment_id):
    from app.services.catalogtb_browser import browser_data
    from app.services.ai.takeoff_pricebook import published_rows
    global _index_devices, _index_prices, _index_links
    devices, prices = browser_data()['items'], published_rows()
    with _index_lock:
        if devices is not _index_devices or prices is not _index_prices:
            _index_devices, _index_prices, _index_links = devices, prices, {}
        if equipment_id not in _index_links:
            device = next((d for d in devices if d['id']==equipment_id),None)
            if device is None:
                return {}
            _index_links[equipment_id] = configuration_links(device,prices)
        return dict(_index_links[equipment_id])


def device_price_diagnostic(equipment_id):
    """Explain availability independently of a price or CAD approval."""
    from app.services.catalogtb_browser import browser_data
    from app.services.ai.takeoff_pricebook import published_rows
    device=next((d for d in browser_data()['items'] if d['id']==equipment_id),None)
    if device is None:return {'status':'not_found','message':'Không tìm thấy thiết bị đang đối chiếu.'}
    if device.get('type')=='MOUNTING_TEMPLATE':
        return {'status':'mounting_reference','message':'Đây là bản vẽ lỗ khoét/lắp đặt, không phải một thiết bị điện độc lập để tính giá. Chọn thiết bị đầy đủ và cấu hình riêng khi bóc tách.'}
    if device.get('type')=='ASSEMBLY_REFERENCE':
        return {'status':'assembly_requires_components','message':'CAD này thuộc cụm chuyển nguồn/lắp đặt có nhiều bộ phận. Cần bóc từng MCCB và phụ kiện theo cấu hình; không lấy giá một MCCB làm giá cả cụm.'}
    from app.services.library_review_scope import exact_price_required
    if not exact_price_required(device):
        return {'status':'optional_price','message':'Cầu đấu/phụ kiện: không yêu cầu khớp chính xác mã và giá trong phạm vi bóc tách hiện tại. Có thể bổ sung giá nhà cung cấp khi cần; không tự lấy giá của thiết bị điện khác.'}
    status=device.get('brand_identification_status')
    messages={
        'not_applicable':'Đây là phụ kiện phổ thông. Cần chọn nhà cung cấp và mã hàng thực tế để đối chiếu giá.',
        'unknown':'Chưa xác định được hãng. Cần kiểm tra nhãn trên thiết bị hoặc tài liệu nguồn trước khi chọn giá.',
        'candidate':'Hãng hiện là ứng viên; cần xác nhận nhãn hãng trước khi liên kết bảng giá.',
        'source_library':'Hãng mới được xác định theo thư viện nguồn. Cần xác nhận hãng và mã trên thiết bị thực tế.'}
    if status!='verified':return {'status':status or 'unknown','message':messages.get(status,messages['unknown'])}
    prices=published_rows()
    own=[r for r in prices if canonical_brand(r['brand'])==canonical_brand(device.get('brand'))]
    if not own:return {'status':'no_brand_prices','message':'Chưa có bảng giá đối chiếu theo nhãn hãng này trong dữ liệu đã công bố.'}
    if device_configuration_links(equipment_id):return {'status':'choices_available','message':''}
    code=str(device.get('product_code') or '').strip()
    if code.upper()=='PM710' and canonical_brand(device.get('brand'))=='Schneider Electric':
        return {'status':'discontinued_model','message':'Schneider đã ngừng thương mại PM710 tại châu Á–Thái Bình Dương từ 30/04/2015. Cần báo giá đúng mã cũ hoặc chọn thiết bị thay thế phù hợp; không tự gán giá PM51xx cho CAD PM710.',
                'source_url':'https://www.se.com/uk/en/faqs/FA264122/'}
    codes=(device.get('ai_identification') or {}).get('cac_ma_dong_san_pham') or []
    codes=[*codes,*((device.get('reviewed_description') or {}).get('price_family_codes') or [])]
    if str(device.get('type') or '').upper()=='TRANSFORMER' and not code:
        return {'status':'missing_transformer_configuration','message':'Đã phân loại là biến áp điều khiển. Cần xác nhận mã, công suất VA và điện áp sơ/thứ cấp để chọn đúng dòng giá; CAD hiện chưa ghi đủ cấu hình này.'}
    if not code and not codes:
        return {'status':'no_device_code','message':'Đã xác định hãng và có bảng giá cùng hãng, nhưng chưa xác nhận mã thiết bị. Mã ứng viên hoặc kích thước hình vẽ chưa đủ để chọn giá.'}
    family_codes={str(c).upper() for c in [code,*codes] if c}
    kind=str(device.get('type') or '').upper().replace(' ','_')
    family_rows=[r for r in own if r.get('category')==kind and str((r.get('specifications') or {}).get('Họ thiết bị') or '').upper() in family_codes]
    if family_rows:
        from app.services.ai.takeoff_pricebook import _values
        available=sorted({int(p) for r in family_rows for p in _values(r,'poles')})
        required=str((device.get('spec') or {}).get('so_cuc') or '')
        pole=re.fullmatch(r'(\d+)P',required,re.I)
        if pole and available and int(pole[1]) not in available:
            return {'status':'different_poles','message':f'Đã có giá dòng {code}, nhưng bảng giá hiện có '+', '.join(f'{p}P' for p in available)+f'; CAD đang xem là {required}. Cần bổ sung dòng giá đúng số cực, không dùng giá khác số cực.'}
    if kind=='TRANSFORMER':
        return {'status':'missing_transformer_configuration','message':'Đã phân loại là biến áp điều khiển. Cần xác nhận mã, công suất VA và điện áp sơ/thứ cấp để chọn đúng dòng giá; CAD hiện chưa ghi đủ cấu hình này.'}
    if code.upper()=='A9D' and canonical_brand(device.get('brand'))=='Schneider Electric':
        return {'status':'incomplete_ordering_code','message':'Đã nhận diện hãng Schneider Electric và tiền tố A9D. A9D chưa phải mã đặt hàng đầy đủ; cần đọc các chữ số còn lại, loại chống rò và cấu hình điện. Nhãn 2P/4P trên mặt CAD được giữ riêng để tránh chọn nhầm RCBO/RCCB.'}
    lookup_kind={'INDICATOR':'LIGHT','PILOTLAMP':'LIGHT','SELECTOR':'SELECTOR_SWITCH','THERMALRELAY':'THERMAL_RELAY','PHASERELAY':'PHASE_RELAY','QUẠT_LỌC_GIÓ_TỦ_ĐIỆN':'FAN'}.get(kind,kind)
    unconstrained=[c for model in family_codes for c in match_device({'brand':device.get('brand'),'category':lookup_kind,'part_number':model},own,candidate_limit=None)['candidates']]
    if not unconstrained:
        return {'status':'no_model_prices','message':f'Đã nhận diện {device.get("brand")} · {device.get("type")} · {code or "/".join(sorted(family_codes))}. Dữ liệu giá đã công bố chưa có mã/họ này đúng loại thiết bị. Cần bổ sung giá đúng mã; không phải chưa phân loại thiết bị.'}
    from app.services.ai.takeoff_pricebook import _values
    ids={c['price_row_id'] for c in unconstrained}
    available=sorted({int(p) for r in own if public_id(r) in ids for p in _values(r,'poles')})
    required=str((device.get('spec') or {}).get('so_cuc') or '')
    pole=re.fullmatch(r'(\d+)P',required,re.I)
    if pole and available and int(pole[1]) not in available:
        return {'status':'different_poles','message':f'Đã có giá đúng dòng {code}, nhưng dữ liệu giá chỉ có '+', '.join(f'{p}P' for p in available)+f'; CAD này là {required}. Cần giá đúng số cực.'}
    return {'status':'no_matching_configuration','message':'Đã có bảng giá cùng hãng, nhưng chưa khớp mã, loại và cấu hình của CAD này. Cần đối chiếu mã đặt hàng, số cực và thông số; không lấy giá của thiết bị khác.'}

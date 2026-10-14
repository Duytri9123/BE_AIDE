"""User-requested takeoff priority; optional prices are never invented."""


def exact_price_required(device):
    kind=str(device.get('type') or device.get('category') or '').upper().replace(' ','_')
    return not (device.get('brand_identification_status')=='not_applicable'
        or device.get('category') in {'Cầu đấu','Khóa','Phíp','Phụ kiện tủ điện','Đố','Đồng'}
        or kind in {'TERMINAL_BLOCK','TERMINAL','ACCESSORY','AUX_CONTACT','AUX_CONTACTS','INTERLOCK','MOUNTING_TEMPLATE'}
        or 'CẦU_ĐẤU' in kind)

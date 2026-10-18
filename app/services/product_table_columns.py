"""Product facts become ordinary price-table columns, including unpriced rows."""
LABELS={'so_cuc':'Số cực','so_cuc_chinh':'Số cực chính','co_khung':'Cỡ khung AF',
        'dong_dinh_muc':'Dòng định mức','dong_dinh_muc_A':'In (A)',
        'dien_ap_dinh_muc':'Điện áp định mức','dien_ap_cuon_hut':'Điện áp cuộn hút',
        'kha_nang_cat':'Khả năng cắt','dong_chinh_dinh':'Dòng chỉnh định',
        'tieu_chuan':'Tiêu chuẩn','cap_chinh_xac':'Cấp chính xác','tan_so_Hz':'Tần số (Hz)'}

def fact_label(key):return LABELS.get(key,key.replace('_',' '))

def table_columns(item):
    spec=item.get('specifications') or {}
    name=spec.get('Tên hàng') or item.get('item_name') or item.get('name') or item.get('sku') or ''
    pairs=[(fact_label(k),v) for k,v in spec.items() if k not in {'Tên hàng','Tên thiết bị','Mã hàng'}
           and not (k=='Mã đặt hàng' and str(v)==str(item.get('sku')))]
    return ['Tên hàng','Mã hàng',*(k for k,v in pairs),'Giá bán'],[name,item.get('sku') or '',*(v for k,v in pairs),'']

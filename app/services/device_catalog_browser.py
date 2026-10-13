"""Customer-facing manufacturer portfolios and published selling-price records."""
import math
from app.services.ai.manufacturer_registry import manufacturer_categories, canonical_brand, CHECKED_DATE
from app.services.device_catalog_engine import strip_accents

CATEGORY_LABELS = {
    'MCB':'MCB', 'MCCB':'MCCB', 'ACB':'ACB', 'RCBO':'RCBO', 'RCCB':'RCCB',
    'CONTACTOR':'Khởi động từ', 'THERMAL_RELAY':'Rơ le nhiệt', 'TIMER':'Timer',
    'ALTERNATING_RELAY':'Rơ le luân phiên', 'RELAY':'Rơ le', 'CT':'Biến dòng',
    'METER':'Đồng hồ đo', 'AMMETER':'Ampe kế', 'VOLTMETER':'Vôn kế',
    'MULTIMETER':'Đồng hồ đa năng', 'LIGHT':'Đèn báo', 'PILOT_LIGHT':'Đèn báo',
    'SELECTOR':'Công tắc chuyển mạch', 'FUSE':'Cầu chì', 'SPD':'Chống sét',
    'VFD':'Biến tần', 'ATS':'Chuyển nguồn', 'SHUNT_TRIP':'Cuộn cắt',
    'AUX_CONTACT':'Tiếp điểm phụ', 'UNDERVOLTAGE_RELEASE':'Cuộn thấp áp',
    'POWER_SUPPLY':'Bộ nguồn', 'TERMINAL':'Cầu đấu', 'PUSHBUTTON':'Nút nhấn',
    'ATS_CONTROLLER':'Bộ điều khiển ATS', 'CAPACITOR':'Tụ bù', 'CB':'Aptomat',
    'ELCB':'Aptomat chống rò', 'ENERGY_METER':'Công tơ điện', 'HMI':'Màn hình HMI',
    'IO':'Mô đun I/O', 'LEVEL_RELAY':'Rơ le mức', 'MOTOR_PROTECTION':'Bảo vệ động cơ',
    'OVERLOAD_RELAY':'Rơ le quá tải', 'PLC':'Bộ điều khiển PLC',
    'POWER_FACTOR_CONTROLLER':'Bộ điều khiển tụ bù', 'RCD':'Thiết bị chống rò',
    'SOFT_STARTER':'Khởi động mềm',
}

def label(code):
    return CATEGORY_LABELS.get(code, code.replace('_', ' '))

def build_catalog_page(priced_items, custom_prices, *, q='', brand='', category='', skip=0, limit=30):
    rows = {}
    for item in priced_items:
        code = str(item.get('sku') or item.get('ma') or '').strip()
        maker = canonical_brand(item.get('brand_display') or item.get('brand'))
        source = item.get('source') or {}
        if not isinstance(source, dict): source = {'document':str(source)}
        entry = {'id':str(item.get('catalog_id') or maker+':'+code), 'sku':code,
                 'name':item.get('name') or item.get('n') or code, 'brand':maker,
                 'category':str(item.get('category') or item.get('t') or '').upper(),
                 'price':item.get('price') or item.get('g'), 'source_label':'Catalog nhà cung cấp',
                 'source_url':source.get('url'), 'updated_at':source.get('updated_at') or source.get('date'),
                 'price_note':'Giá theo catalog; xác nhận VAT và chiết khấu với nhà cung cấp.'}
        rows[(maker,code)] = entry
    for item in custom_prices:
        maker = canonical_brand(item.get('brand'))
        key = str(item.get('key') or '')
        code = str(item.get('sku') or (key if ':' not in key else ''))
        rows[(maker,code or key)] = {
            'id':'published:'+key, 'sku':code, 'name':item.get('name') or code,
            'brand':maker, 'category':str(item.get('category') or '').upper(),
            'price':item.get('price'), 'source_label':'Giá do quản trị cập nhật',
            'source_url':None, 'updated_at':item.get('updated_at'),
            'price_note':'Giá tham khảo; xác nhận VAT, chiết khấu và thời hạn áp dụng.'}
    items = [row for row in rows.values() if isinstance(row['price'], (int,float))
             and not isinstance(row['price'], bool) and math.isfinite(row['price']) and row['price'] > 0]
    makers = {}
    for name, info in manufacturer_categories().items():
        name = canonical_brand(name)
        makers[name] = {'name':name, 'categories':[
            {'code':code, 'label':label(code), 'source':evidence['source'], 'checked_date':evidence['checked_date']}
            for code,evidence in sorted(info['categories'].items())], 'price_count':0}
    for row in items:
        makers.setdefault(row['brand'], {'name':row['brand'], 'categories':[], 'price_count':0})
        makers[row['brand']]['price_count'] += 1
    categories = sorted({code for maker in makers.values() for code in [c['code'] for c in maker['categories']]} | {i['category'] for i in items})
    normalize = lambda text: strip_accents(str(text)).casefold()
    query = normalize(q.strip())
    filtered = [i for i in items if (not brand or i['brand']==canonical_brand(brand))
                and (not category or i['category']==category)
                and query in normalize(' '.join(str(i[k] or '') for k in ('sku','name','brand','category')))]
    filtered.sort(key=lambda row:(str(row['updated_at'] or ''),row['brand'],row['sku']),reverse=True)
    return {'brands':sorted(makers.values(),key=lambda m:m['name']),
            'categories':[{'code':c,'label':label(c)} for c in categories],
            'items':filtered[skip:skip+limit], 'total':len(filtered), 'priced_total':len(items),
            'checked_date':CHECKED_DATE, 'skip':skip, 'limit':limit}

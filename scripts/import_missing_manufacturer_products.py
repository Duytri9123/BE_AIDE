"""Import published product references for manufacturers missing from the pricebook.

Prices are optional; no CAD matching or generated ordering-code combinations.
Downloaded source responses remain in ignored tmp/.
"""
import hashlib,html,json,re
from pathlib import Path
import httpx
import pymupdf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/brand-gap-research'
OUT.mkdir(exist_ok=True)
records=[]

def add(brand,sku,name,category,url,spec=None,price=None,vat='unknown'):
    records.append(dict(id='manufacturer-gap:'+hashlib.sha256(f'{brand}:{sku}'.encode()).hexdigest()[:24],
        brand=brand,sku=sku,item_name=name,name=name,category=category,group=category,
        specifications=spec or {},price=price,currency='VND',source_url=url,
        checked_at='2026-10-18',vat_status=vat,information_kind='manufacturer_catalog'))

def get(url):
    response=httpx.get(url,follow_redirects=True,timeout=35)
    response.raise_for_status()
    return response

def main():
    # Literal model names in manufacturer datasheets, never suffix expansion.
    for series,models in (
        ('LRS-150',('LRS-150-12','LRS-150-15','LRS-150-24','LRS-150-36','LRS-150-48')),
        ('LRS-350',('LRS-350-3.3','LRS-350-4.2','LRS-350-5','LRS-350-12','LRS-350-15','LRS-350-24','LRS-350-36','LRS-350-48'))):
        url=f'https://www.meanwell.com/Upload/PDF/{series}/{series}-SPEC.PDF'
        for sku in models:
            add('MEAN WELL',sku,'Bộ nguồn '+sku,'POWER_SUPPLY',url,
                {'Điện áp ra DC (V)':sku[len(series)+1:],'Dòng sản phẩm':series})
    # Public manufacturer store API: all listed KDE products and their own attributes.
    for page in range(1,30):
        url=f'https://kdeelectric.vn/wp-json/wc/store/v1/products?per_page=100&page={page}'
        data=json.loads((OUT/'kde.json').read_text(encoding='utf8')) if page==1 and (OUT/'kde.json').exists() else get(url).json()
        (OUT/f'kde-{page}.json').write_text(json.dumps(data),encoding='utf8')
        for product in data:
            if not product.get('sku'):continue
            spec={a['name']:', '.join(t['name'] for t in a.get('terms',[])) for a in product.get('attributes',[])}
            origin=spec.get('Thương Hiệu/ Xuất Xứ','').upper()
            if 'KDE' not in origin:continue
            name=html.unescape(product['name'])
            category='CT' if 'Biến dòng' in name else 'VOLTMETER' if 'Volt' in name else 'AMMETER' if 'Ampe' in name else 'ACCESSORY'
            prices=product.get('prices') or {}
            # Variable products carry a starting price, not a confirmed configuration price.
            price=int(prices['price']) if product.get('type')=='simple' and prices.get('currency_code')=='VND' and str(prices.get('price','')).isdigit() and int(prices['price'])>0 else None
            spec.pop('Mã Sản Phẩm',None)
            add('KDE',product['sku'],name,category,product['permalink'],spec,price,'included')
        if len(data)<100:break
    url='https://robot.com.vn/collections/on-ap-role/products.json?limit=250'
    products=json.loads((OUT/'robot.json').read_text(encoding='utf8'))['products'] if (OUT/'robot.json').exists() else get(url).json()['products']
    for product in products:
        for variant in product.get('variants',[]):
            if not variant.get('sku'):continue
            amount=variant.get('price')
            price=int(float(amount)) if amount and float(amount)>0 else None
            add('ROBOT',variant['sku'],product['title'],'VOLTAGE_STABILIZER',
                'https://robot.com.vn/products/'+product['handle'],{'Dải điện áp vào':variant['title']},price)
    emka='https://www.emka.com/products/category/safety-quarter-turns-with-insert'
    for sku,feature in [('1000-U202-01','Hai rãnh 3 mm, mở phải'),('1000-U204-01','Hai rãnh 3 mm, mở trái'),
        ('1000-U206-01','Hai rãnh 5 mm, mở phải'),('1000-U208-01','Hai rãnh 5 mm, mở trái'),
        ('1000-U210-01','Vuông 6 mm'),('1000-U212-01','Vuông 7 mm'),('1000-U214-01','Vuông 8 mm'),('1000-U216-01','Tam giác 7 mm')]:
        add('EMKA',sku,'Khóa tủ an toàn '+sku,'CABINET_LOCK',emka,{'Kiểu đầu khóa':feature})
    for sku in ('1000-U426','1000-U432','1000-U499','1000-U500','1000-SU125','1000-SU951-LI','1000-SU209-LI','1057-U3-01'):
        add('EMKA',sku,'Khóa tủ '+sku,'CABINET_LOCK','https://www.emka.com/products/category/quarter-turns-selection-pre-assembled-with-simple-insert')
    wohner='https://www.woehner.de/fileadmin/Downloads/15_Manuale/EN_Manual_2020-Update_4-complete--Doppelseiten.pdf'
    for sku,poles in [('01602','2P'),('01495','3P'),('01500','3P'),('01485','4P'),('01508','3P'),('01357','4P')]:
        add('Wöhner',sku,'Giá đỡ thanh cái '+sku,'BUSBAR_SUPPORT',wohner,{'Số cực':poles})
    rittal='https://www.rittal.com/com-en/ebook/cat33/pubData/SEO/Page_396.html'
    for sku,voltage in [('3240.100','230 VAC'),('3240.110','115 VAC'),('3240.124','24 VDC'),
        ('3241.100','230 VAC'),('3241.110','115 VAC'),('3241.124','24 VDC')]:
        add('Rittal',sku,'Quạt lọc tủ điện '+sku,'FAN',rittal,{'Điện áp định mức':voltage,'Kích thước mặt (mm)':'255 × 255'})
    for sku,name in [('3240.200','Lọc thoát khí'),('3243.200','Lọc thoát khí'),('3172.100','Tấm lọc thay thế'),
        ('3182.100','Tấm lọc mịn'),('3240.080','Nắp che nước'),('3110.000','Bộ điều nhiệt tủ điện'),
        ('3114.200','Bộ hiển thị và điều nhiệt'),('3118.000','Bộ điều khiển độ ẩm'),('3120.200','Bộ điều tốc quạt')]:
        add('Rittal',sku,name+' '+sku,'ACCESSORY',rittal)
    add('KACON','K25-21SB22','Nút nhấn có vòng chọn K25-21SB22','PUSHBUTTON',
        'https://www.kacon.com.cn/product/542.html',{'Dòng sản phẩm':'K22/K25'})
    for sku in ('SCB8-63','SCB8-63H','SCB8LE-63','SCB8-125D','SL7N-63'):
        add('Suntree',sku,'Aptomat '+sku,'RCBO' if 'LE' in sku else 'MCB',
            'https://www.suntree-electric.com/product-model-selection-manuals',{'Dòng sản phẩm':sku})
    add('Trend / Honeywell','IQ4E','Bộ điều khiển IQ4E','CONTROLLER',
        'https://buildings.honeywell.com/ca/en/products/by-category/control-panels/building-controls/plant-and-integration-controllers/iq4e-controller',
        {'Kết nối':'Ethernet, TCP/IP','Giao tiếp':'XML'})
    # A Vietnamese fuse brand, distinct from Omega Engineering instrumentation.
    add('Omega','OMG-FS32X','Đế cầu chì có đèn báo OMG-FS32X','FUSE',
        'https://www.thegioidien.com/PrCatalogue/OMEGA-Fuse10x38.pdf',
        {'Điện áp định mức':'690 VAC','Dòng định mức':'32 A','Kích thước ruột chì':'10 × 38 mm','Lắp đặt':'DIN rail 35 mm'})
    cml='https://edisun.vn/products/den-bao-nut-nhan-cml'
    for sku,name in [('LA39-11','Nút nhấn tự nhả không đèn'),('LA39-11S','Nút nhấn giữ không đèn'),
        ('LA39-11D','Nút nhấn tự nhả có đèn'),('LA39-11DS','Nút nhấn giữ có đèn')]:
        add('CML',sku,name+' '+sku,'PUSHBUTTON',cml)
    path=ROOT/'app/data/external_product_information.json'
    payload=json.loads(path.read_text(encoding='utf8'))
    imported_ids={row['id'] for row in records}
    payload['items']=[row for row in payload['items'] if row['id'] not in imported_ids]+records
    payload['checked_at']='2026-10-18'
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    from collections import Counter
    print(json.dumps({'imported':len(records),'brands':dict(Counter(r['brand'] for r in records))}))

if __name__=='__main__':main()

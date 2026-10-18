"""Read exact Phoenix terminal prices and reviewed Leipole filter offers."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]


def main():
    checked=datetime.now(timezone.utc).isoformat();rows=[]
    def add(brand,sku,kind,price,url,seller,spec,vat='unknown',excerpt=''):
        rows.append(dict(id='web:'+hashlib.sha1(url.encode()).hexdigest()[:16],sku=sku,name=sku,
            brand=brand,category=kind,price=price,currency='VND',source_url=url,source_label=seller,
            source_kind='web_seller',checked_at=checked,vat_status=vat,specifications=spec,
            source_excerpt=excerpt,price_note='Giá niêm yết nhà cung cấp; kiểm tra VAT và số lượng tại thời điểm đặt hàng.'))
    for slug,model,order,kind in [('uk-5-n-3004362','UK 5 N','3004362','TERMINAL_BLOCK'),
                                   ('clipfix-35-5-3022276','CLIPFIX 35-5','3022276','TERMINAL_STOP')]:
        url='https://www.kva.com.vn/'+slug
        response=httpx.get(url,timeout=35,follow_redirects=True);response.raise_for_status()
        text=BeautifulSoup(response.text,'html.parser').get_text(' ',strip=True)
        match=re.search(re.escape(model+' - '+order)+r'\s+Giá bán:\s*(\d{1,3}(?:\.\d{3})+) đ\s+SKU:\s*'+order,text)
        if not match:raise ValueError('Seller identity/price layout changed: '+model)
        add('Phoenix Contact',model,kind,int(match[1].replace('.','')),url,'KVA',{'Mã hàng':order},excerpt=match[0])
    # Supplier's public category listing reviewed 2026-10-16; all three are
    # passive .300 filters, never motorized .230 fans.
    url='https://hoplongtech.com/category/quat-thong-gio-tu-dien'
    for sku,price in [('FKL6621.300',52338),('FKL6622.300',63835),('FKL6623.300',92149)]:
        add('Leipole',sku,'FILTER',price,url+'#'+sku,'Hợp Long',{'Loại':'Tấm gió có lọc bụi; không có động cơ'},
            vat='excluded' if sku=='FKL6621.300' else 'unknown',excerpt=f'Tấm gió có lọc bụi {sku} Leipole · {price:,}đ; public indexed supplier listing reviewed 2026-10-16')
    for sku,kind,price,url,seller,spec in [
        ('A9A15310','SOCKET',386000,'https://www.nguyenkhoitech.com/2021/05/a9a15310-o-cam-gang-ray.html','Nguyên Khôi',{'Số cực':'2P+E','In (A)':'16','Điện áp':'250VAC'}),
        ('K1F027MLH','SELECTOR_METER',1161875,'https://bandodien.com/dong-ho-tu-dien-relay-bao-ve/chuyen-mach-volt-schneider-k1f027mlh-thiet-bi-dien.html','Liên Minh Nguyễn',{'Loại':'Chuyển mạch volt','Số vị trí':'7'}),
        ('A9S65363','SWITCH_DISCONNECTOR',1119844,'https://www.thietbidiendgp.vn/products/acti-9-isw-isolating-switch-3p-32a#A9S65363','Đặng Gia Phát',{'Số cực':'3P','In (A)':'63','Điện áp':'415VAC','Nguồn cấu hình':'Dòng A9S65363 trong bảng biến thể; không lấy giá A9S60332 của tiêu đề trang'}),
    ]:
        add('Schneider Electric',sku,kind,price,url,seller,spec,excerpt=f'{sku}: {price:,} VND; exact public seller product/variant row reviewed 2026-10-16')
    path=ROOT/'app/data/web_catalog_offers.json';data=json.loads(path.read_text(encoding='utf8'))
    merged={r['id']:r for r in data['items']}
    for row in rows:merged[row['id']]=row
    data['items']=list(merged.values());path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Imported accessory prices:',len(rows))


if __name__=='__main__':main()

"""Collect explicit live product-card prices, excluding struck prices and ranges."""
import asyncio
import hashlib
import json
import re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

SOURCES=[('https://etinco.vn/ats-btb/','BTB Electric','ATS'),
 ('https://etinco.vn/tu-bu-nuintek/','Nuintek','CAPACITOR'),
 ('https://etinco.vn/tu-bu-samwha/','Samwha','CAPACITOR'),
 ('https://etinco.vn/tu-bu-mikro/','Mikro','CAPACITOR'),
 ('https://etinco.vn/tu-bu-epcos/','TDK / EPCOS','CAPACITOR'),
 ('https://etinco.vn/tu-bu-shizuki/','Shizuki','CAPACITOR'),
 ('https://etinco.vn/tu-bu-ducati/','Ducati Energia','CAPACITOR'),
 ('https://etinco.vn/thiet-bi-dien-emic/','EMIC','METER')]

def parse_card(card,brand,category,collection,checked):
    title=card.select_one('h3.product-title a');price=card.select_one('.price')
    if title is None or price is None:return None
    name=title.get_text(' ',strip=True);code=name.split('|')[0].strip()
    ct_ratio = None
    if brand == 'EMIC':
        model = re.search(r'\bEM\dH\d+[A-Z]?\b', name, re.I)
        ratios = re.findall(r'\b(\d+)\s*/\s*(\d+)\s*A\b', name, re.I)
        if not model or len(ratios) != 1 or 'Biến dòng' not in name:
            return None
        ct_ratio = ratios[0]
        code = model[0].upper()+' '+ct_ratio[0]+'/'+ct_ratio[1]+'A'
        category = 'CT'
    elif '|' not in name or not re.fullmatch(r'[A-Za-z0-9._/-]+',code) or not re.search(r'\d',code):return None
    amounts=[]
    for span in price.select('span'):
        if span.select('span') or 'line-through' in span.get('class',[]) or span.find_parent('del'):continue
        value=span.get_text(' ',strip=True)
        if re.search(r'[-–—]',value) or not re.search(r'đ|₫|VND',value,re.I):continue
        digits=re.sub(r'\D','',value)
        if digits:amounts.append(int(digits))
    if len(set(amounts))!=1 or amounts[0]<=0:return None
    url=title.get('href','')
    if urlparse(url).hostname!='etinco.vn':return None
    specs={}
    if ct_ratio:
        specs.update({'In (A)': ct_ratio[0], 'Dòng thứ cấp (A)': ct_ratio[1],
                      'Tỷ số CT': ct_ratio[0]+'/'+ct_ratio[1]+'A'})
    for label,pattern in [('Điện áp',r'\b\d+(?:[.,]\d+)?\s*(?:V|VAC)\b'),
                          ('Dung lượng bù',r'\b\d+(?:[.,]\d+)?\s*kVAr\b'),
                          ('Dòng định mức',r'\b\d+(?:[.,]\d+)?\s*A\b'),
                          ('Số cực',r'\b[1-4]P\b')]:
        match=re.search(pattern,name,re.I)
        if match:specs[label]=match[0]
    return {'id':'web:'+hashlib.sha1(url.encode()).hexdigest()[:16],'sku':code,'name':name,
            'brand':brand,'category':category,'price':amounts[0],'currency':'VND',
            'source_url':url,'collection_url':collection,'source_label':'Etinco',
            'source_kind':'web_seller','checked_at':checked,'specifications':specs,
            'price_note':'Giá bán hiện tại trên thẻ sản phẩm, VAT chưa xác định; phạm vi nhập là trang đã đọc.'}

async def refresh():
    checked=datetime.now(timezone.utc).isoformat();offers=[];errors=[];reviews=[]
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        sem=asyncio.Semaphore(3)
        async def read(source):
            url,brand,category=source
            async with sem:
                try:
                    response=await client.get(url);response.raise_for_status()
                    if urlparse(str(response.url)).hostname!='etinco.vn':raise ValueError('Unexpected domain')
                    soup=BeautifulSoup(response.text,'html.parser');accepted=[]
                    for card in soup.select('article.term-product__item'):
                        row=parse_card(card,brand,category,url,checked)
                        if row:accepted.append(row)
                    offers.extend(accepted)
                    reviews.append({'brand':brand,'title':soup.h1.get_text(' ',strip=True) if soup.h1 else brand,
                        'url':url,'source_label':'Etinco','checked_at':checked,'effective_date':None,
                        'source_updated_at':None,'status':'live_seller_collection','accepted_rows':len(accepted)})
                except Exception as exc:errors.append({'url':url,'error':type(exc).__name__})
        await asyncio.gather(*(read(s) for s in SOURCES))
    root=Path(__file__).resolve().parents[1];path=root/'app/data/web_catalog_offers.json'
    payload=json.loads(path.read_text(encoding='utf8'));merged={r['source_url']:r for r in payload['items']}
    for row in offers:merged[row['source_url']]=row
    payload['items']=list(merged.values());payload['checked_at']=checked;payload['additional_source_errors']=errors
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(path)
    path=root/'app/data/catalog_documents.json';data=json.loads(path.read_text(encoding='utf8'));existing={d['url']:d for d in data['items']}
    existing.update({r['url']:r for r in reviews});data['items']=list(existing.values())
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'accepted_rows':len(offers),'collections':[{k:r[k] for k in ('brand','accepted_rows')} for r in reviews],
                      'errors':errors},ensure_ascii=False))

if __name__=='__main__':asyncio.run(refresh())

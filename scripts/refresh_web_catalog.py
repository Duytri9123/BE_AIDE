"""Refresh a bounded set of public seller offers; never invent a model or price."""
import asyncio, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

SOURCES = [
    ('https://codienhaiau.com/series/ls-bkn/','LS Electric','MCB'),
    ('https://codienhaiau.com/series/chint-nxb-63/','CHINT','MCB'),
    ('https://codienhaiau.com/category/abb/mcb-abb/','ABB','MCB'),
    ('https://codienhaiau.com/series/omron-h3cr/','Omron','TIMER'),
    ('https://codienhaiau.com/category/autonics/timer-autonics/','Autonics','TIMER'),
    ('https://codienhaiau.com/category/selec/timer-selec/','Selec','TIMER'),
    ('https://codienhaiau.com/category/den-bao/','', 'LIGHT'),
]
DESTINATION = Path(__file__).resolve().parents[1] / 'app/data/web_catalog_offers.json'

def selling_price(element):
    if element is None: return None
    sale = element.select_one('ins')
    amounts = (sale or element).select('.woocommerce-Price-amount')
    values = set()
    for amount in amounts:
        if sale is None and amount.find_parent('del'): continue
        text = amount.get_text(' ',strip=True)
        if '₫' not in text and 'VND' not in text.upper(): continue
        if re.search(r'[–—]',element.get_text()) and sale is None: return None
        digits = re.sub(r'\D','',text)
        if digits: values.add(int(digits))
    return next(iter(values)) if len(values)==1 and next(iter(values))>0 else None

async def refresh():
    checked = datetime.now(timezone.utc).isoformat()
    semaphore = asyncio.Semaphore(4)
    errors, offers = [], []
    async with httpx.AsyncClient(timeout=25,follow_redirects=True,headers={'User-Agent':'ELQuote-Catalog/1.0'}) as client:
        async def fetch(url):
            if urlparse(url).hostname!='codienhaiau.com': raise ValueError('Unapproved source domain')
            async with semaphore:
                response=await client.get(url)
                response.raise_for_status()
                if urlparse(str(response.url)).hostname!='codienhaiau.com': raise ValueError('Unexpected redirect')
                return BeautifulSoup(response.text,'html.parser')
        async def source(collection,brand,category):
            try:
                listing=await fetch(collection)
                links=[]
                for product in listing.select('li.product'):
                    title=product.select_one('.woocommerce-loop-product__title')
                    anchor=product.select_one('a.woocommerce-LoopProduct-link')
                    if not title or not anchor or selling_price(product.select_one('.price')) is None: continue
                    url=anchor.get('href','')
                    if url not in links and urlparse(url).path.startswith('/product/'): links.append(url)
                    if len(links)==6: break
                for url in links:
                    try:
                        detail=await fetch(url)
                        summary=detail.select_one('.summary')
                        if summary is None: continue
                        title=summary.select_one('h1.product_title')
                        sku=summary.select_one('.sku')
                        price=selling_price(summary.select_one('.devvn_price') or summary.select_one('p.price, span.price'))
                        if not title or not sku or not price: continue
                        name=title.get_text(' ',strip=True);code=sku.get_text(' ',strip=True)
                        if code in ('N/A','') or re.search(r'Đế|base|socket',name,re.I): continue
                        maker=brand
                        if not maker:
                            maker=next((b for b in ('Schneider','CHINT','Hanyoung','IDEC','Autonics','Morele','Andeli') if re.search(r'\b'+b+r'\b',name,re.I)),'')
                            if maker=='Schneider': maker='Schneider Electric'
                        if not maker: continue
                        offers.append({'id':'web:'+hashlib.sha1(url.encode()).hexdigest()[:16],
                            'sku':code,'name':name,'brand':maker,'category':category,'price':price,
                            'currency':'VND','source_label':'Cơ Điện Hải Âu','source_url':url,
                            'collection_url':collection,'checked_at':checked,'source_kind':'web_seller',
                            'price_note':'Giá bán niêm yết trên website tại lúc tra cứu; VAT, vận chuyển và chiết khấu cần xác nhận.'})
                    except (httpx.HTTPError,ValueError) as exc: errors.append({'url':url,'error':type(exc).__name__})
            except (httpx.HTTPError,ValueError) as exc: errors.append({'url':collection,'error':type(exc).__name__})
        await asyncio.gather(*(source(*row) for row in SOURCES))
    previous=json.loads(DESTINATION.read_text(encoding='utf8')) if DESTINATION.exists() else {'items':[]}
    # Preserve previous offers for a failed source, with their original check date.
    merged={item['source_url']:item for item in previous['items']}
    for offer in offers: merged[offer['source_url']]=offer
    if not offers: raise RuntimeError('No source offers verified; existing data preserved')
    payload={'checked_at':checked,'items':list(merged.values()),'errors':errors}
    DESTINATION.parent.mkdir(parents=True,exist_ok=True)
    temporary=DESTINATION.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    temporary.replace(DESTINATION)
    print(json.dumps({'verified':len(offers),'total':len(merged),'brands':sorted({r['brand'] for r in offers}),'errors':len(errors)},ensure_ascii=False))

if __name__=='__main__': asyncio.run(refresh())

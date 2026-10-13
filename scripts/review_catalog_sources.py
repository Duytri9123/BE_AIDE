"""Check one observed external candidate per requested manufacturer; no price guessing."""
import asyncio
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.customer_manufacturers import CUSTOMER_MANUFACTURERS
from app.services.device_catalog_browser import load_catalog_documents,load_supplier_items,load_web_offers
from app.services.ai.manufacturer_registry import canonical_brand

CANDIDATES={
 'Schneider Electric':'https://www.se.com/vn/vi/download/document/MasterPriceBook/',
 'ABB':'https://new.abb.com/low-voltage/products',
 'Siemens':'https://www.dienhathe.com/bang-gia-thiet-bi-dien-siemens-2026/',
 'Hager':'https://www.thietbidiendgp.vn/bang-gia/hager',
 'Legrand':'https://legrandhcm.vn/catalogue/',
 'BTB Electric':'https://btb-electric.com/vi/danh-muc-tai-lieu/catalogue/',
 'Mitsubishi Electric':'https://www.saigonelectric.vn/bang-gia/41-thiet-bi-dong-cat.html',
 'Fuji Electric':'https://www.fujielectric.com/fcs/document/download/download_catalog.html',
 'LS Electric':'https://www.ls-electric.com.vn/en/solution/l-series-mcb/',
 'Shihlin':'https://circuit-breaker.seec.com.tw/Templates/att/All_product.pdf',
 'CHINT':'https://www.chintglobal.com/global/en/products/low-voltage/iec/final-power-distribution/nxb-63.html',
 'Andeli':'https://vnecco.com/andeli',
 'Sino - Vanlock':'https://www.thietbidiendgp.vn/blogs/bang-gia',
 'Vinakip':'https://role24h.com/bang-gia',
 'Omron':'https://industrial.omron.com.tr/tr/news-discover/news/pricelist-2026',
 'Delta':'https://www.deltaww.com/en-US/products/industrial-automation',
 'Yaskawa':'https://codienhaiau.com/category/yaskawa/',
 'Danfoss':'https://maybompanasonic.net/bang-gia-bien-tan-danfoss.html',
 'INVT':'https://tudonghoatoancau.com/wp-content/uploads/2026/04/Bien-tan-Trung-Quoc-INVT.pdf',
 'IDEC':'https://vnecco.com/bang-gia-idec',
 'Hanyoung Nux':'https://hanyoungnux.vn/download/',
 'Samwha':'https://etinco.vn/tu-bu-samwha/',
 'TDK / EPCOS':'https://etinco.vn/tu-bu-epcos/',
 'Shizuki':'https://etinco.vn/tu-bu-shizuki/',
 'Nuintek':'https://etinco.vn/tu-bu-nuintek/',
 'Mikro':'https://etinco.vn/tu-bu-mikro/',
 'SK':'https://chodansinh.net/bo-dieu-khien-tu-bu-sk-pro176395.html',
 'Ducati Energia':'https://etinco.vn/tu-bu-ducati/',
 'Selec':'https://thietbibenthanh.com/bang-gia-thiet-bi-dien-selec-moi-109-26.html',
 'Delixi':'https://swe.com.vn/bang-gia',
 'Morele':'https://role24h.com/thiet-bi-dien-morele',
 'EMIC':'https://etinco.vn/thiet-bi-dien-emic/',
}

async def review():
    checked=datetime.now(timezone.utc).isoformat();results={};sem=asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=20,follow_redirects=True) as client:
        async def read(maker,url):
            async with sem:
                record={'brand':maker,'url':url,'checked_at':checked,'prices_approved':False}
                try:
                    response=await client.get(url);response.raise_for_status()
                    content=response.headers.get('content-type','')
                    record.update(status='candidate_fetched_pending_review',content_type=content)
                    if 'html' in content:
                        soup=BeautifulSoup(response.text,'html.parser')
                        record['title']=soup.title.get_text(' ',strip=True) if soup.title else maker
                    else:record['title']=maker+' · Tài liệu tham khảo'
                    # Identity and currency cannot be inferred from an article headline.
                    if maker=='SK':record['identity_status']='supplier_identity_review_required'
                    if maker=='Omron':record['currency_status']='non_vnd_market_reference_not_imported'
                except Exception as exc:record.update(status='fetch_failed',error=type(exc).__name__)
                results[maker]=record
        await asyncio.gather(*(read(maker,CANDIDATES[maker]) for maker in CUSTOMER_MANUFACTURERS))
    documents=load_catalog_documents();prices=load_supplier_items()+load_web_offers()
    rows=[]
    for maker in CUSTOMER_MANUFACTURERS:
        count=sum(canonical_brand(p['brand'])==maker for p in prices)
        refs=[d for d in documents if canonical_brand(d['brand'])==maker]
        rows.append({'brand':maker,'checked_at':checked,'priced_rows':count,'documents':len(refs),
                     'external_candidate':results[maker],
                     'status':'price_rows_available_partial' if count else 'no_verified_numeric_price'})
    report={'checked_at':checked,'brands':rows,'complete_price_coverage':False,
            'priced_manufacturers':sum(bool(r['priced_rows']) for r in rows),
            'total_priced_rows':sum(r['priced_rows'] for r in rows)}
    path=ROOT/'app/data/catalog_coverage_review.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'checked_manufacturers':len(rows),'priced_manufacturers':report['priced_manufacturers'],
                     'total_priced_rows':report['total_priced_rows'],
                     'fetch_failures':[m for m,r in results.items() if r['status']=='fetch_failed']},ensure_ascii=False))

if __name__=='__main__':asyncio.run(review())

"""Review every requested maker against published supplier indexes, preserving gaps."""
import asyncio
import json
import re
import sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.customer_manufacturers import CUSTOMER_MANUFACTURERS,CUSTOMER_ALIASES
from app.services.ai.manufacturer_registry import canonical_brand
from app.services.device_catalog_engine import strip_accents

async def refresh():
    checked=datetime.now(timezone.utc).isoformat();documents=[];errors=[]
    aliases={strip_accents(k).casefold():v for k,v in CUSTOMER_ALIASES.items()}
    aliases.update({strip_accents(k).casefold():v for k,v in {'Schneider':'Schneider Electric','Mitsubishi':'Mitsubishi Electric',
        'Fuji':'Fuji Electric','LS':'LS Electric','Shihlin Electric':'Shihlin','Hanyoung':'Hanyoung Nux','Epcos':'TDK / EPCOS'}.items()})
    async with httpx.AsyncClient(timeout=35,follow_redirects=True) as client:
        index='https://www.saigonelectric.vn/bang-gia/41-thiet-bi-dong-cat.html'
        response=await client.get(index);response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        urls={index}|{urljoin(index,a['href']) for a in soup.select('a[href]')
                       if '/bang-gia/' in a['href'] and a['href'].endswith('.html')}
        sem=asyncio.Semaphore(3)
        async def read(url):
            async with sem:
                try:
                    response=await client.get(url);response.raise_for_status()
                    page=BeautifulSoup(response.text,'html.parser')
                    for link in page.select('li a[href]'):
                        title=link.get_text(' ',strip=True)
                        if not title.startswith('Bảng giá') and not title.startswith('Bảng Giá'):continue
                        if title=='Tải xuống':continue
                        normal=strip_accents(title).casefold()
                        matches=[(alias,maker) for alias,maker in aliases.items() if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',normal)]
                        if not matches:continue
                        maker=max(matches,key=lambda x:len(x[0]))[1]
                        if maker not in CUSTOMER_MANUFACTURERS:continue
                        container=link.find_parent('li').get_text(' ',strip=True)
                        date=re.findall(r'\b(\d{2})/(\d{2})/(\d{4})\b',container)
                        updated='-'.join(reversed(date[-1])) if date else None
                        download=urljoin(url,link['href'])
                        documents.append({'brand':maker,'title':title,'url':download,
                            'source_label':'Điện Sài Gòn','index_url':url,'source_updated_at':updated,
                            'checked_at':checked,'download_urls':[download],'effective_date':None,
                            'status':'source_document_pending_import'})
                except Exception as exc:errors.append({'url':url,'error':type(exc).__name__})
        await asyncio.gather(*(read(url) for url in sorted(urls)))
    path=ROOT/'app/data/catalog_documents.json';payload=json.loads(path.read_text(encoding='utf8'))
    existing={d['url']:d for d in payload['items']}
    for document in documents:existing[document['url']]=document
    payload['items']=list(existing.values());payload['checked_at']=checked
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    prices=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
    prices+=json.loads((ROOT/'app/data/web_catalog_offers.json').read_text(encoding='utf8'))['items']
    coverage=[]
    for maker in CUSTOMER_MANUFACTURERS:
        refs=[d for d in payload['items'] if canonical_brand(d['brand'])==maker]
        count=sum(canonical_brand(p['brand'])==maker for p in prices)
        current=[d for d in refs if (d.get('source_updated_at') or '')[:4]=='2026']
        coverage.append({'brand':maker,'checked_at':checked,'priced_rows':count,'documents':len(refs),
                         'documents_updated_2026':len(current),'status':'price_rows_available_partial' if count
                         else 'current_document_pending_import' if current else 'historical_reference_only' if refs
                         else 'source_not_found_in_checked_indexes'})
    report={'checked_at':checked,'brands':coverage,'index_errors':errors,'complete_price_coverage':False}
    (ROOT/'app/data/catalog_coverage_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'new_documents':len({d['url'] for d in documents}),'reviewed_brands':len(coverage),
                      'brands_without_documents':[r['brand'] for r in coverage if not r['documents']],
                      'index_errors':len(errors)},ensure_ascii=False))

if __name__=='__main__':asyncio.run(refresh())

"""Cache public manufacturer documents already cited by the library for identity review."""
import asyncio
import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
import httpx
import pymupdf
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'outputs/catalog-identity-documents'
HOSTS=('abb.com','se.com','schneider-electric.com','ls-electric.com','mitsubishielectric.com',
       'chintglobal.com','chint.net','emic.com.vn','hynux.com','hanyoungnux.com',
       'lightstar.co.jp','lightstar.co.kr','leipole.net','seec.com.tw','omron.com',
       'itmikro.com.my','siemens.com','support.industry.siemens.com','emka.com','rittal.com',
       'phoenixcontact.com','woehner.de','meanwell.com','pfannenberg.com','smartgen.com.cn',
       'deepseaelectronics.com','pce.pl','pcelectric.at','leipole.com','suntree-electric.com','mitex.vn')
EXTRA=[
 ('Schneider Electric','https://download.schneider-electric.com/files?p_Doc_Ref=Easy_Catalogue&p_File_Ext=.PDF'),
 ('Schneider Electric','https://iportal.se.com/Contents/docs/ATV212_CATALOG.PDF'),
 ('Schneider Electric','https://download.schneider-electric.com/files?filename=Catalog&p_Doc_Ref=DIA2ED2160311EN'),
 ('Schneider Electric','https://download.schneider-electric.com/files?filename=Catalog&p_Doc_Ref=DIA2ED2140502EN'),
 ('Siemens','https://cache.industry.siemens.com/dl/files/121/109478121/att_851433/v1/s71200_system_manual_en-US_en-US.pdf'),
 ('ABB','https://catalogo-generale.abb.com/avviamento-motori/accessori-e-ricambi-contattori-e-minicontattori/CAL5-11'),
 ('ABB','https://new.abb.com/low-voltage/zh/products/system-pro-m/terminal-distribution-protection-products/sh200'),
 ('ABB','https://new.abb.com/low-voltage/tr/products/devre-kesiciler/tmax-t/kilavuz-videolar-t7-t7m'),
 ('Siemens','https://mall.industry.siemens.com/mall/en/ww/catalog/products/10045647?regionUrl=WW'),
 ('Schneider Electric','https://download.schneider-electric.com/files?p_Doc_Ref=CA909006NL&p_File_Ext=.PDF'),
 ('Schneider Electric','https://www.se.com/es/es/faqs/FAQ000240682/'),
 ('LightStar','https://www.lightstar.co.jp/product/view%26idx%3D187'),
 ('LightStar','https://thegioidien.com/PrCatalogue/Lightstar-Catalog_KBD.pdf'),
 ('Leipole','https://leipole.pl/wp-content/uploads/2024/12/LEIPOLE-2023.pdf'),
 ('LS Electric','https://www.ls-electric.com/upload/customer/download/1627/Electric%20Products_E_1703.pdf'),
 ('Mikro','https://itmikro.com.my/zct-40s-60s-80s-120-210s-earth-leakage-relay/'),
 ('Phoenix Contact','https://www.phoenixcontact.com/de-de/produkte/durchgangsklemme-uk-3-n-3001501'),
 ('Phoenix Contact','https://www.phoenixcontact.com/en-gb/products/feed-through-terminal-block-uk-3-n-3001501?type=pdf'),
 ('Leipole','https://www.leipole.com/UserFiles/Article/download/20%E8%BF%87%E6%BB%A4%E5%99%A8CE_NgTrMpZU.pdf'),
 ('MITEX','https://mitex.vn/san-pham/bien-dong-do-luong-ha-the-kieu-bd01/'),
 ('Hanyoung Nux','https://www.thegioidien.com/fckupload/Hanyoung_HYBT.pdf'),
 ('EMIC','https://emic.com.vn/vn/cong-to-dien-tu-3-pha-nhieu-bieu-gia'),
 ('Suntree','https://www.suntree-electric.com/search/product'),
 ('LightStar','https://www.thegioidien.com/PrCatalogue/Lightstar-Catalog_KBF.pdf'),
 ('Hanyoung Nux','https://mme-ae.com/wp-content/uploads/2022/08/HYT-series.pdf'),
 ('Hanyoung Nux','https://www.components247.com/wp-content/uploads/2026/01/HYT_catalogue_en_251112.pdf'),
 ('Hanyoung Nux','https://www.hynux.com/data/main.php?down=2448(Terminal-Block_RoHS2).pdf&file_name=Terminal-Block_RoHS2.pdf'),
 ('ABB','https://library.e.abb.com/public/819d3b51acd74e06b1b5c7b2c09a12b4/AX%20main%20catalogue_Catalogue_ZH_1SXF101005C2001_RevJ-20230726.pdf'),
 ('Mitsubishi Electric','https://www.mitsubishielectric.com/dl/fa/document/catalog/lvsw/l02031eng/L%28NA%2902031ENG-L_21B.pdf'),
 ('CHINT','https://www.chintglobal.com/content/dam/chint/global/product-center/low-voltage/iec/secondary-power-distribution/mccb/nxm/catalog/NXM-MCCB-Catalog.pdf'),
 ('LS Electric','https://www.ls-electric.com/upload/customer/download/1213/Metasol_MCCB-ELCB_Technical%20Manual_E.pdf'),
 ('EMIC','https://emic.com.vn/img/files/bien-dong/CT.pdf'),
 ('Schneider Electric','https://ckm-content.se.com/ckmContent/sfc/servlet.shepherd/document/download/0698V00000lzD3hQAE'),
]


def permitted(url):
    host=urlparse(url).hostname or ''
    return url.startswith('https://') and (any(host==h or host.endswith('.'+h) for h in HOSTS) or url in {u for _,u in EXTRA})


def document_text(content,content_type):
    if content.startswith(b'%PDF'):
        with pymupdf.open(stream=content,filetype='pdf') as doc:
            return {'format':'pdf','pages':[{'page':i+1,'text':p.get_text()} for i,p in enumerate(doc)]}
    if 'html' in content_type or b'<html' in content[:1500].lower():
        soup=BeautifulSoup(content,'html.parser')
        for tag in soup.select('script,style,nav,footer,header'):tag.decompose()
        return {'format':'html','pages':[{'page':1,'text':soup.get_text(' ',strip=True)}]}
    return {'format':'unsupported','pages':[]}


async def main():
    FOLDER.mkdir(parents=True,exist_ok=True);sources={}
    def add(url,brand):
        if isinstance(url,str) and permitted(url):sources.setdefault(url,set()).add(brand or '')
    for path in (ROOT/'data/CatalogTB').rglob('thong_tin_thiet_bi.json'):
        raw=json.loads(path.read_text(encoding='utf8'));brand=raw.get('hang_xac_nhan')
        for url in [raw.get('tai_lieu_hang'),*(raw.get('nguon_tham_khao') or [])]:add(url,brand)
        for option in (raw.get('catalog_tham_khao') or {}).get('options') or []:
            if option.get('basis') in {'documented_source_model','manufacturer_family_document'}:add(option.get('source_url'),option.get('brand'))
    for brand,url in EXTRA:add(url,brand)
    semaphore=asyncio.Semaphore(4);results=[]
    async with httpx.AsyncClient(timeout=30,follow_redirects=True,headers={'User-Agent':'CatalogIdentityResearch/1.0'}) as client:
        # Download pages are HTML landing pages, not the actual technical PDF.
        # Follow only the explicit manufacturer-provided downloadUrl metadata.
        async def discover(url,brands):
            if 'se.com/' not in url or '/download/document/' not in url:return
            try:
                async with semaphore:
                    response=await client.get(url);response.raise_for_status()
                urls=re.findall(r'downloadUrl:"([^"]+)"',response.text)
                for linked in urls[:1]:
                    linked=unescape(linked)
                    if linked.startswith('//'):linked='https:'+linked
                    if permitted(linked):sources.setdefault(linked,set()).update(brands)
            except Exception:pass
        await asyncio.gather(*(discover(url,brands) for url,brands in list(sources.items())))
        async def fetch(url,brands):
            cache=FOLDER/(hashlib.sha256(url.encode()).hexdigest()[:24]+'.json')
            if cache.is_file():
                result=json.loads(cache.read_text(encoding='utf8'))
                if result.get('status') in {'fetched','fetch_failed'}:results.append(result);return
            result={'url':url,'brands':sorted(brands),'checked_at':'2026-10-17'}
            host=urlparse(url).hostname or ''
            result['document_host_type']='manufacturer' if any(host==h or host.endswith('.'+h) for h in HOSTS) else 'manufacturer_document_mirror_pending_visual_review'
            async with semaphore:
                try:
                    response=await client.get(url);response.raise_for_status()
                    if not permitted(str(response.url)):raise ValueError('Redirect left manufacturer domains')
                    parsed=await asyncio.to_thread(document_text,response.content,response.headers.get('content-type',''))
                    if not parsed['pages']:raise ValueError('No readable document pages')
                    result.update(status='fetched',final_url=str(response.url),sha256=hashlib.sha256(response.content).hexdigest(),**parsed)
                    if parsed['format']=='pdf':
                        output=cache.with_suffix('.pdf');output.write_bytes(response.content);result['local_pdf']=output.relative_to(ROOT).as_posix()
                except Exception as error:result.update(status='fetch_failed',error=type(error).__name__+': '+str(error)[:220])
            cache.write_text(json.dumps(result,ensure_ascii=False),encoding='utf8');results.append(result)
            print(f"Documents {len(results)}/{len(sources)}: {result['status']} {urlparse(url).hostname}",flush=True)
        await asyncio.gather(*(fetch(url,brands) for url,brands in sources.items()))
    manifest={'checked_at':'2026-10-17','sources':[{k:v for k,v in r.items() if k!='pages'} for r in results]}
    (FOLDER/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Fetched',sum(r.get('status')=='fetched' for r in results),'of',len(results),'manufacturer documents',flush=True)


if __name__=='__main__':asyncio.run(main())

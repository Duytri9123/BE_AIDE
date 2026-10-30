"""Preserve and convert distributor-hosted LS BK AC source drawings."""
import hashlib,json,re,subprocess,urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/CatalogTB/LS/NguonBenNgoai'
PAGE='https://2sk.co.kr/bkac/?gal_idx=540075&gmode=view'

def main():
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    opener.addheaders=[('User-Agent','Mozilla/5.0')]
    html=opener.open(PAGE,timeout=60).read().decode('utf8')
    links=re.findall(r'href="([^"]+)"[^>]*>(BK[^<]+\.dwg)</a>',html)
    for link,name in links:
        if name not in ['BK05S-T3.dwg','BK10,20,30,40S.dwg']:continue
        ident='2SK-BK05S-T3' if name.startswith('BK05') else '2SK-BK10-40S'
        folder=BASE/ident;folder.mkdir(exist_ok=True)
        target=folder/'source.dwg';url='https://2sk.co.kr'+link
        if not target.exists():
            data=opener.open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':PAGE}),timeout=60).read()
            assert data.startswith(b'AC10'),(name,data[:30])
            target.write_bytes(data)
        meta=dict(source_url=url,source_page=PAGE,source_filename=name,
                  source_host_type='distributor',checked_at='2026-10-26',
                  sha256=hashlib.sha256(target.read_bytes()).hexdigest(),review_status='pending_drawing_review')
        (folder/'source.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
        dxf=folder/'source.dxf'
        if not dxf.exists():
            script=folder/'convert.scr'
            script.write_text('FILEDIA\n0\nSECURELOAD\n2\n_.DXFOUT\n'+dxf.as_posix()+'\n_Version\n2018\n16\n_.QUIT\n_Y\n',encoding='ascii')
            with (folder/'convert.log').open('wb') as log:
                result=subprocess.run(['C:/Program Files/Autodesk/AutoCAD 2022/accoreconsole.exe','/i',str(target),'/s',str(script),'/l','en-US'],stdout=log,stderr=log,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
            assert dxf.is_file(),result.returncode
        print(ident,target.stat().st_size,'converted',flush=True)

if __name__=='__main__':main()

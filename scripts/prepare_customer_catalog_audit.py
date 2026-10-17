"""Prepare actual customer API data and audit every CAD view for FE verification."""
import hashlib
import json
import re
from pathlib import Path
from collections import Counter
from app.services.catalogtb_browser import _build_browser_data
from app.services.customer_equipment_information import customer_browser,customer_information_rows,public_view_id
from app.services.library_catalog_information import information_rows
from app.services.equipment_library import CATALOG_TB_ROOT
from app.api.v1.endpoints.equipment_library import _cad_view_file

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'tmp/customer-catalog-qa'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    raw=_build_browser_data();safe=customer_browser(raw)
    html=(CATALOG_TB_ROOT/'index.html').read_text(encoding='utf8')
    old=json.loads(re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',html,re.S)[1])
    old_rows={p['id']:p.get('catalog_information') for p in old['profiles']}
    prices={};files={};problems=[];views=0;brands=Counter()
    for i,(internal,public) in enumerate(zip(raw['items'],safe['items']),1):
        rows=old_rows.get(internal['id'])
        if rows is None or internal.get('brand') in {'Hanyoung Nux','Omron'}:rows=information_rows(internal)
        prices[internal['id']]=customer_information_rows(rows,internal)
        brands[public.get('brand') or 'Chưa xác định']+=1
        if not public['views'] or public['primary_view'] not in {v['id'] for v in public['views']}:
            problems.append({'device':internal['id'],'issue':'invalid_primary_view'})
        hashes={}
        for source,view in zip(internal['views'],public['views']):
            views+=1
            try:
                owner=view['preview'].split('/')[2]
                relative=_cad_view_file(owner,view['id'],'preview')
                path=(CATALOG_TB_ROOT/relative.removeprefix('catalogtb/')).resolve()
                if not path.is_relative_to(CATALOG_TB_ROOT.resolve()):raise ValueError('Invalid path')
                content=path.read_bytes()
                files[view['preview'].split('?')[0]]=str(path)
                digest=hashlib.sha256(content).hexdigest()
                if digest in hashes and hashes[digest]!=view['face']:
                    problems.append({'device':internal['id'],'view':view['id'],'issue':'same_image_different_face_labels','labels':[hashes[digest],view['face']]})
                hashes[digest]=view['face']
                _cad_view_file(owner,view['id'],'dxf')
            except Exception as error:problems.append({'device':internal['id'],'view':view['id'],'issue':'asset_error','error':str(error)})
        if i%100==0:print(f'Audited customer data {i}/{raw["total"]}',flush=True)
    # Visual comparison images use ordinary catalog previews; map both public and
    # existing comparison URLs through the same resolved asset, never fake images.
    for item in safe['items']:
        for candidate in item.get('visual_candidates',[]):
            url=candidate['comparison_preview'].split('?')[0]
            parts=url.split('/')
            if len(parts)>4:
                try:files[url]=str(CATALOG_TB_ROOT/_cad_view_file(parts[2],parts[4],'preview').removeprefix('catalogtb/'))
                except Exception:pass
    (OUT/'data.json').write_text(json.dumps({'browser':safe,'information':prices,'assets':files},ensure_ascii=False),encoding='utf8')
    summary={'devices':len(safe['items']),'views':views,'devices_with_information':sum(bool(v) for v in prices.values()),
        'information_rows':sum(map(len,prices.values())),'brands':dict(brands),'issues':problems,
        'scope':'Customer API payload plus actual asset resolver; geometric projection identity still requires visual review.'}
    (ROOT/'docs/customer-catalog-all-device-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'brands','issues'}}),flush=True)
    print(f'View issues: {len(problems)}',flush=True)


if __name__=='__main__':main()

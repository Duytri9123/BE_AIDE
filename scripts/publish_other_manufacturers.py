"""Publish only product facts and public links, keyed by opaque catalog IDs."""
import json
import hashlib
from pathlib import Path
from app.services.equipment_library import CATALOG_TB_ROOT
from app.services.customer_equipment_information import reference_options

def main():
    profiles={}
    for path in CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json'):
        raw=json.loads(path.read_text(encoding='utf-8-sig'))
        brand=raw.get('hang_xac_nhan') or (raw.get('nhan_dien_web') or {}).get('brand_candidate')
        if not brand or raw.get('browser_hidden'):continue
        _,other=reference_options({'brand':brand,'catalog_references':raw.get('catalog_tham_khao') or {}})
        if not other:continue
        for row in other:row['price']=None
        relative=path.relative_to(CATALOG_TB_ROOT).as_posix()
        profiles['TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]]=other
    dest=Path(__file__).resolve().parents[1]/'app/data/published_other_manufacturers.json'
    dest.write_text(json.dumps({'schema_version':1,'profiles':profiles},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Published other-manufacturer references:',len(profiles),'profiles,',sum(len(v) for v in profiles.values()),'references')

if __name__=='__main__':main()

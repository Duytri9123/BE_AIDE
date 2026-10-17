"""Export reviewed information, without CAD files, secrets or selling prices."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def main():
    profiles={}
    for p in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
        d=json.loads(p.read_text(encoding='utf-8-sig'))
        references=d.get('catalog_tham_khao') or {}
        for option in references.get('options',[]):
            assert option['price']=='---'
        row={'catalog_tham_khao':references,'ten_san_pham':d.get('ten_san_pham')}
        if (d.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code'):
            row['catalog_information_type']=d['nhan_dien_ai']['loai_thiet_bi_code']
        if d.get('nhom_thu_vien'):
            row.update({k:d[k] for k in ('nhom_thu_vien','ten_san_pham','ma_dong_san_pham') if k in d})
        profiles[p.relative_to(CAT).as_posix()]=row
    # Extraction evidence is an internal artifact, never a tracked publication.
    dest=ROOT/'tmp/catalog_private_information.json'
    dest.parent.mkdir(exist_ok=True)
    payload='{"schema_version":1,"prices":"---","profiles":{\n'+',\n'.join(
        json.dumps(key,ensure_ascii=False)+':'+json.dumps(value,ensure_ascii=False,separators=(',',':'))
        for key,value in profiles.items())+'\n}}\n'
    pending=dest.with_suffix('.tmp')
    pending.write_text(payload,encoding='utf8')
    pending.replace(dest)
    from scripts.export_customer_catalog_publication import main as publish_customer
    publish_customer(private_information=profiles)
    from app.services.catalogtb_browser import _build_browser_data, _snapshot_path
    snapshot=_build_browser_data()
    _snapshot_path().write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf8')
    print('Published catalog information:',len(profiles),'profiles;',dest.stat().st_size,'bytes')


if __name__=='__main__':main()

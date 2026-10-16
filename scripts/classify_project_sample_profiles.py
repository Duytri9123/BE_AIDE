"""Publish source project CAD under its manufacturer; keep paths and CAD intact."""
import json
from pathlib import Path
from app.services.catalogtb_browser import _build_browser_data, _snapshot_path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'data/CatalogTB/ProjectSamples'
ASSIGNMENTS={
    'BKN_1P':('LS','MCB LS BKN · 1P','BKN'),
    'BKN_2P':('LS','MCB LS BKN · 2P','BKN'),
    'BKN_3P':('LS','MCB LS BKN · 3P','BKN'),
    'MC12AF':('LS','Khởi động từ LS MC-12a · CAD MC12AF',None),
    'Selector':('Chint','Công tắc chuyển mạch CHINT',None),
    'Timer24h':('Chint','Timer lịch 24H CHINT',None),
    'SupplyS8FS':('Omron','Bộ nguồn Omron S8FS-C05024J','S8FS-C05024J'),
    'FuseSingle':('RISESUN','Cầu chì RISESUN RT18-32','RT18-32'),
    'Relay125SRQ':('Rơ le','Rơ le 125SRQ',None),
}


def main():
    changed=[]
    for folder,(category,name,family) in ASSIGNMENTS.items():
        path=FOLDER/folder/'thong_tin_thiet_bi.json'
        d=json.loads(path.read_text(encoding='utf-8-sig'))
        d['nhom_thu_vien']=category
        d['nhom']=category
        d['ten_san_pham']=name
        if family:
            d['ma_dong_san_pham']=family
        if folder.startswith('BKN_'):
            d['ten_kieu']='BKN'
            d['nhan_dien_ai']['cac_ma_dong_san_pham']=['BKN']
            d['nhan_dien_ai']['pham_vi_ma']='product_family'
            d['thong_so']['so_cuc']=d['nhan_dien_ai']['so_cuc']
            d['catalog_tham_khao']['observed_specifications']['so_cuc']=d['nhan_dien_ai']['so_cuc']
            for option in d['catalog_tham_khao']['options']:
                if option['basis'] in {'source_profile','cad_reference_code'}:
                    option.update(model='BKN',basis='source_profile')
        d['library_classification_review']={
            'basis':'User requested manufacturer/family classification instead of ProjectSamples',
            'source_paths_preserved':True,'manufacturer_unassigned':not bool(d.get('hang_xac_nhan'))}
        path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        changed.append({'profile':path.relative_to(ROOT/'data/CatalogTB').as_posix(),'category':category,'name':name})
    snapshot=_build_browser_data()
    assert not any(p['category']=='ProjectSamples' for p in snapshot['items'])
    _snapshot_path().write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf8')
    (ROOT/'docs/project-sample-manufacturer-classification.json').write_text(json.dumps({'updated':changed,'profiles':len(changed),'source_geometry_changed':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'updated':len(changed),'visible':snapshot['total'],'project_group_remaining':0},ensure_ascii=False))


if __name__=='__main__':main()

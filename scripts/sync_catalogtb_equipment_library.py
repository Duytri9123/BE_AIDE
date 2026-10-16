"""Publish CatalogTB profiles into the private equipment catalog without SKU guesses."""
import hashlib,json,sqlite3,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'data/CatalogTB';OUT=ROOT/'_agent_index';OUT.mkdir(exist_ok=True)
path=OUT/'equipment_catalog.sqlite'
if path.exists():shutil.copy2(path,OUT/'equipment_catalog.before_catalogtb.sqlite')
with sqlite3.connect(path) as db:
    db.executescript('''CREATE TABLE IF NOT EXISTS equipment(catalog_id TEXT PRIMARY KEY,brand TEXT,category TEXT,model TEXT,display_name TEXT,record_type TEXT,price_vnd INTEGER,cad_status TEXT,record_json TEXT NOT NULL);
    CREATE VIRTUAL TABLE IF NOT EXISTS equipment_fts USING fts5(catalog_id UNINDEXED,brand,category,model,display_name,description,tokenize='unicode61 remove_diacritics 2');''')
    db.execute('DELETE FROM equipment');db.execute('DELETE FROM equipment_fts')
    count=0
    for p in sorted(ROOT.rglob('thong_tin_thiet_bi.json')):
        d=json.loads(p.read_text(encoding='utf-8-sig'));views=[]
        if d.get('browser_hidden'):continue
        for v in d.get('cad_don',[]):
            folder=p.parent/'CadDon'/v['id_hinh_goc'];rel='catalogtb/'+folder.relative_to(ROOT).as_posix()
            if not (folder/'ban_ve.dxf').is_file() or not (folder/'xem_truoc.svg').is_file():continue
            views.append({'id':v['id_hinh_goc'],'name':v.get('nhan_hien_thi') or v.get('huong_nhin'),'state':v.get('huong_nhin'),'preview':{'path':rel+'/xem_truoc.svg'},'dxf':{'path':rel+'/ban_ve.dxf'},'placement':v.get('bo_tri_trong_tu',{})})
        if not views:continue
        cid='TB-'+hashlib.sha1(p.relative_to(ROOT).as_posix().encode()).hexdigest()[:16]
        primary=next((v for v in views if v['id']==d.get('cad_chen_tu',{}).get('id_hinh_goc')),views[0])
        brand=d.get('hang_xac_nhan') or (d.get('nhom') if d.get('nhom') in ('LS','Chint','Schneider','Mitsubishi','ABB','Shihlin','O-Sung') else None)
        rec={'catalog_id':cid,'record_type':'source_cad_device_or_assembly','display_name':d.get('ten_san_pham') or d['ten_kieu'],'model':d.get('ma_dong_san_pham') or d['ten_kieu'],'brand':brand,'brand_verified':bool(d.get('hang_xac_nhan')),'category':d.get('ban_chat') or d['nhom'],'description':d.get('cong_dung',''),'specifications':{'poles':None,'current_a':None,'current_display':None,'breaking_capacity_ka':None},'price':None,'cad':{'status':'source_cad_unverified_sku','views':views,'default_view_id':primary['id'],'preview':primary['preview'],'dxf':primary['dxf'],'match_basis':d.get('muc_do_xac_nhan','')},'source_record':{'dataset':'CatalogTB','row_id':cid},'evidence':{'profile_id':cid,'review_required':d.get('needs_review',True)},'warnings':[d.get('muc_do_xac_nhan','Cần xác nhận mã, mặt và đơn vị CAD trước dùng.')],'auto_select':False}
        db.execute('INSERT INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',(cid,brand,rec['category'],rec['model'],rec['display_name'],rec['record_type'],None,rec['cad']['status'],json.dumps(rec,ensure_ascii=False)))
        aliases=' '.join(d.get('tu_khoa_tim_kiem',[]));db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',(cid,brand,rec['category'],rec['model'],rec['display_name'],rec['description']+' '+aliases));count+=1
    total=db.execute('SELECT count(*) FROM equipment').fetchone()[0]
with sqlite3.connect(path) as db:
    (OUT/'equipment_catalog.jsonl').write_text('\n'.join(row[0] for row in db.execute('SELECT record_json FROM equipment'))+'\n',encoding='utf-8')
manifest=OUT/'manifest.json';data=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {};data.update(catalogtb_profiles=count,records=total,private_assets=True);manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Private equipment library:',count,'CatalogTB profiles;',total,'total records')

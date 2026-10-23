import hashlib,json,sqlite3,sys
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
from download_abb_ct_sources import SOURCES
ROOT=Path(__file__).resolve().parents[1]/'data/CatalogTB'
sys.path.insert(0,str(ROOT.parents[1]))

def main(families=None, report_name="abb-ct-faces-2026-10-20", brand="ABB", category="CT", profile_root=None, refresh=True):
 if families is None: families=SOURCES
 with sqlite3.connect(ROOT/'_agent_index/equipment_catalog.sqlite') as db:
  for family in families:
   path=(ROOT/profile_root/family if profile_root else ROOT/'BienDong'/brand/family)/'thong_tin_thiet_bi.json';profile=json.loads(path.read_text(encoding='utf8'))
   record_kind=(profile.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code') or category
   model=profile.get('ma_dong_san_pham') or family
   cid='TB-'+hashlib.sha1(path.relative_to(ROOT).as_posix().encode()).hexdigest()[:16]
   if profile.get('browser_hidden'):
    db.execute('DELETE FROM equipment WHERE catalog_id=?',(cid,));db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,));continue
   views=[]
   for v in profile['cad_don']:
    relative='catalogtb/'+(path.parent/v['duong_dan']).parent.relative_to(ROOT).as_posix()
    views.append({'id':v['id_hinh_goc'],'name':v['nhan_hien_thi'],'state':v['huong_nhin'],
       'preview':{'path':relative+'/xem_truoc.svg'},'dxf':{'path':relative+'/ban_ve.dxf'},'placement':v['bo_tri_trong_tu']})
   primary=views[0]
   record={'catalog_id':cid,'record_type':'source_cad_device_or_assembly','display_name':profile['ten_san_pham'],'model':model,'brand':brand,'brand_verified':True,'category':record_kind,
    'description':profile['cong_dung'],'specifications':{'poles':None,'current_a':None,'current_display':None,'breaking_capacity_ka':None},'price':None,
    'cad':{'status':'source_cad_unverified_sku','views':views,'default_view_id':primary['id'],'preview':primary['preview'],'dxf':primary['dxf'],'match_basis':profile['muc_do_xac_nhan']},
    'source_record':{'dataset':'CatalogTB','row_id':cid},'evidence':{'profile_id':cid,'review_required':True},'warnings':[profile['muc_do_xac_nhan']],'auto_select':False}
   db.execute('INSERT OR REPLACE INTO equipment VALUES(?,?,?,?,?,?,?,?,?)',(cid,brand,record_kind,model,record['display_name'],record['record_type'],None,record['cad']['status'],json.dumps(record,ensure_ascii=False)))
   db.execute('DELETE FROM equipment_fts WHERE catalog_id=?',(cid,))
   db.execute('INSERT INTO equipment_fts VALUES(?,?,?,?,?,?)',(cid,brand,record_kind,model,record['display_name'],' '.join(profile['tu_khoa_tim_kiem'])))
  total=db.execute('SELECT count(*) FROM equipment').fetchone()[0]
 manifest=ROOT/'_agent_index/manifest.json';data=json.loads(manifest.read_text(encoding='utf8'));data.update(records=total,catalogtb_profiles=total)
 manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
 report=json.loads((ROOT.parents[1]/('docs/'+report_name+'.json')).read_text(encoding='utf8'))
 canvas=Image.new('RGB',(1600,max(200,((len(report)+3)//4)*200)),'white');draw=ImageDraw.Draw(canvas)
 for index,item in enumerate(report):
  im=ImageOps.contain(Image.open(ROOT/item['path']/'preview.png').convert('RGB'),(365,155))
  x=(index%4)*400+(400-im.width)//2;y=(index//4)*200+30
  canvas.paste(im,(x,y));draw.text(((index%4)*400+8,(index//4)*200+8),item['family']+' '+item['view'],fill='black')
 canvas.save(ROOT.parents[1]/('docs/'+report_name+'.png'))
 if refresh:
  from app.services.catalogtb_browser import _refresh_browser_data
  _refresh_browser_data(ROOT)
 print(f'Published {len(families)} {brand} {category} families / {len(report)} views; browser refresh={refresh}')

if __name__=='__main__':main()

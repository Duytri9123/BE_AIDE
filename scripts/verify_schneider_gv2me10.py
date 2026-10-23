import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.catalogtb_browser import browser_page
from app.services.customer_equipment_information import customer_browser,public_view_id
from app.api.v1.endpoints.equipment_library import _cad_view_file
from app.services.equipment_library import asset_bytes
ROOT=Path(__file__).resolve().parents[1]
def main():
 a=customer_browser(browser_page(brand='Schneider',limit=1000))
 b=customer_browser(browser_page(brand='Schneider Electric',limit=1000))
 assert {i['id'] for i in a['items']}=={i['id'] for i in b['items']}
 assert 'Schneider' not in a['brands'] and a['brands'].count('Schneider Electric')==1
 # Brand filters also intentionally include generic devices with this maker's references.
 assert not any(i.get('brand')=='Schneider' for i in a['items'])
 own=[i for i in a['items'] if i.get('brand')=='Schneider Electric']
 relative='Schneider/ThietBi/OFFICIAL-MCADPD0003997-GV2ME10/thong_tin_thiet_bi.json'
 cid='TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
 item=next(i for i in a['items'] if i['id']==cid)
 assert len(item['views'])==6
 assert len({v['face'] for v in item['views']})==6
 reads=0
 for v in item['views']:
  assert 'Kích thước mặt CAD ngang×cao (mm)' in v['spec']
  for field in ['dxf','preview']:
   assert len(asset_bytes(_cad_view_file(cid,v['id'],field)))>100;reads+=1
 assert any(o['model']=='GV2ME10' for o in item['catalog_references']['options'])
 result={'brand':'Schneider Electric','alias_filter_equal':True,'visible_items':len(own),'visible_views':sum(len(i['views']) for i in own),'added_model':'GV2ME10','added_faces':6,'verified_asset_reads':reads,'frontend_commit':'26a4e007','remaining_single_view_items':sum(len(i['views'])==1 for i in own),'dimensions':[{'face':v['face'],'spec':v['spec']} for v in item['views']]}
 (ROOT/'docs/schneider-update-2026-10-21/gv2me10-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(result))
if __name__=='__main__':main()

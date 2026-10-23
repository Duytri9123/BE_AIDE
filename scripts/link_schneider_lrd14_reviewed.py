"""Reuse the existing manufacturer CAD once for another observed compatible reference."""
import json,shutil,sys
from pathlib import Path
from ls_native_writer import ROOT,CAT,price_option
from publish_abb_ct_index import main as publish
def main():
 rel='Schneider/ThietBi/OFFICIAL-MCADPD0004675-LRD21/thong_tin_thiet_bi.json';p=CAT/rel;raw=json.loads(p.read_text(encoding='utf8'))
 if any(o['model']=='LRD14' for o in raw['catalog_tham_khao']['options']):raise RuntimeError('Already linked')
 out=ROOT/'docs/four-brands-additions-2026-10-22';backup=out/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
 rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items'];row=next(r for r in rows if r['brand']=='Schneider Electric' and r['sku']=='LRD14')
 option=price_option(row,brand='Schneider Electric');option['specifications'].update({'Dải chỉnh định (A)':'7–10','Cấp tác động':'10A'});option['basis']='manufacturer_same_cad_document_observed';option['compatibility_evidence']={'product_url':'https://www.se.com/uk/en/product/LRD14/','cad_page':'https://nuovaelva.it/store/en/shop/brands/TEL/items/LRD14','checked_at':'2026-10-22','cad_ref':'MCADPD0004675','six_link_file_hashes_match_existing':True,'scope':'Family geometry only, ordered electrical configuration remains separate'}
 raw['catalog_tham_khao']['options'].append(option)
 raw['ma_dong_san_pham']='LRD14 / LRD21';raw['nhan_dien_ai']['cac_ma_dong_san_pham']=['LRD14','LRD21']
 raw['tu_khoa_tim_kiem']=list(dict.fromkeys(raw.get('tu_khoa_tim_kiem',[])+['LRD14','7–10 A']))
 raw['ten_san_pham']=raw['ten_kieu']='Rơ le nhiệt Schneider Electric LRD14 / LRD21 · 7–10 / 12–18 A · 10A'
 raw['thong_so']['Dải chỉnh định (A)']='LRD14: 7–10; LRD21: 12–18'
 raw['nguon_tham_khao'].append(option['compatibility_evidence']['cad_page'])
 p.write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf8')
 publish([p.parent.name],report_name='schneider-full-faces-2026-10-21',brand='Schneider Electric',category='THERMAL_RELAY',profile_root='Schneider/ThietBi',refresh=False)
 (out/'schneider-lrd14-link.json').write_text(json.dumps(option,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()

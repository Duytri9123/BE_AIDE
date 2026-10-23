"""Customer identity and native model-state regressions from the reported screenshots."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.catalog_publication_policy import public_device_allowed,public_profile_allowed,normalized_brand_labels,selected_model_rows
from app.services.cad.ls_view_coverage import view_coverage

class PublicationTests(unittest.TestCase):
 def test_unresolved_not_procurement_equipment(self):
  for item in [dict(brand='Shihlin',product_code='',display='MCB Shihlin chưa rõ mã'),dict(brand=None,product_code='125SRQ',display='Rơ le 125SRQ'),dict(brand='CHINT',product_code='SRC_012',display='Transformer')]:
   self.assertFalse(public_device_allowed(item))
  self.assertTrue(public_device_allowed(dict(brand_kind='generic',display='Bản lề')))
  self.assertTrue(public_device_allowed(dict(brand='Mitsubishi Electric',product_code='NF125-SV',display='MCCB NF125-SV')))
 def test_manufacturer_alias_is_one_folder(self):
  self.assertEqual(normalized_brand_labels(['Schneider','Schneider Electric','LS','LS Electric']),['LS Electric','Schneider Electric'])
 def test_unknown_identity_is_rejected_before_loading_its_cad(self):
  import tempfile
  from app.services import catalogtb_browser
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);profile=root/'LS/ThietBi/unknown/thong_tin_thiet_bi.json';profile.parent.mkdir(parents=True)
   profile.write_text(json.dumps({'hang_xac_nhan':'LS','ten_san_pham':'MCB LS chưa rõ mã','ma_dong_san_pham':'','nhan_dien_ai':{'loai_thiet_bi_code':'MCB'},'cad_don':[{'id_hinh_goc':'unknown','duong_dan':'bad.dxf','huong_nhin':'Mặt trước'}]}),encoding='utf8')
   (root/'index.html').write_text('<script id="catalog-data" type="application/json">{"profiles":[]}</script>',encoding='utf8')
   with patch.object(catalogtb_browser,'CATALOG_TB_ROOT',root),patch('app.services.catalog_view_health.source_displayable',side_effect=AssertionError('Unresolved CAD must not be loaded')):
    self.assertEqual(catalogtb_browser._build_browser_data(information_override={})['items'],[])
 def test_source_label_review_is_retained_only_for_unchanged_drawing(self):
  import tempfile,hashlib
  from app.services import catalog_source_identification as source
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'device/thong_tin_thiet_bi.json';p.parent.mkdir();drawing=p.parent/'front.dxf';drawing.write_bytes(b'original native drawing')
   raw={'hang_xac_nhan':'LS','ma_dong_san_pham':None,'ten_san_pham':'Contactor LS chưa rõ mã','cad_don':[{'id_hinh_goc':'front','duong_dan':'front.dxf'}]}
   registry=root/'reviews.json';registry.write_text(json.dumps({'profiles':{p.relative_to(root).as_posix():{'source_fingerprint':source.source_fingerprint(raw),'status':'documented_source_label','documented_models':[{'model':'MC-9'}],'views':[{'path':drawing.relative_to(root).as_posix(),'sha256':hashlib.sha256(drawing.read_bytes()).hexdigest()}]}}}),encoding='utf8')
   with patch.object(source,'PATH',registry):
    self.assertTrue(public_profile_allowed(raw,p,root))
    drawing.write_bytes(b'changed drawing')
    self.assertFalse(public_profile_allowed(raw,p,root))
 def test_generic_support_uses_current_recognized_type(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'support/thong_tin_thiet_bi.json'
   self.assertTrue(public_profile_allowed({'ten_san_pham':'Xa sau 20×55 mm','ban_chat':'Support','nhan_dien_ai':{'loai_thiet_bi_code':'MountingSupport'}},p,root))
 def test_current_annotations_are_front_states_not_missing_front(self):
  status=view_coverage([{'label':'Mặt trước · '+str(a)+' A'} for a in [9,12,18,25,32]]+[{'label':'Mặt sau'},{'label':'Mặt bên'}])
  self.assertEqual(status['available_faces'],['front','rear'])
  self.assertEqual(set(status['missing_faces']),{'left','right','top','bottom'})
 def test_native_mc12_is_distinct_from_mc9(self):
  root=Path(__file__).resolve().parents[1]/'data/CatalogTB/LS/ThietBi/MC_9'
  d=json.loads((root/'thong_tin_thiet_bi.json').read_text(encoding='utf8'))
  fronts={v['model_codes'][0]:v for v in d['cad_don'] if len(v.get('model_codes',[]))==1}
  self.assertEqual(set(fronts),{'MC-9','MC-12','MC-18','MC-25','MC-32'})
  self.assertNotEqual((root/fronts['MC-9']['duong_dan']).read_bytes(),(root/fronts['MC-12']['duong_dan']).read_bytes())
 def test_price_filter_uses_selected_model_before_pagination(self):
  device={'id':'test','brand':'LS Electric','product_code':'MC-9 / MC-12','views':[{'model_codes':['MC-9']},{'model_codes':['MC-12']} ]}
  rows=[{'sku':'MC-9','item_name':'MC-9 220V','match_scope':'source_family'}, {'sku':'MC-12','item_name':'MC-12 220V','match_scope':'source_family'}, {'sku':'MC-120','item_name':'MC-120','match_scope':'source_family'}]
  result=selected_model_rows(device,rows,'MC-12')
  self.assertEqual([r['sku'] for r in result],['MC-12'])
  with self.assertRaises(ValueError):selected_model_rows(device,rows,'MC-12a')
 def test_bvw_t_is_rccb_without_mutating_pricebook(self):
  from app.services.reviewed_product_taxonomy import reviewed_price_row
  from app.services.library_reference_prices import reference_matches
  raw={'id':'bvw','brand':'Mitsubishi Electric','item_name':'BVW-T 2P 25A 30mA','sku':'123456','category':'MCB'}
  corrected=reviewed_price_row(raw)
  self.assertEqual(corrected['category'],'RCCB');self.assertEqual(raw['category'],'MCB')
  self.assertEqual(reference_matches({'brand':'Mitsubishi Electric','model':'123456','source_row_id':'bvw'},'RCCB',[raw]),[corrected])
  self.assertEqual(reference_matches({'brand':'Mitsubishi Electric','model':'123456','source_row_id':'bvw'},'MCB',[raw]),[])
 def test_mitsubishi_breaking_rating_is_voltage_and_model_specific(self):
  from app.services.customer_technical_specs import qualified_breaking_specs
  self.assertEqual(qualified_breaking_specs('Mitsubishi Electric','NF250-HV')['Icu tại 415 V AC (kA)'],'70')
  self.assertEqual(qualified_breaking_specs('Mitsubishi Electric','NF250-HV')['Icu tại 400 V AC (kA)'],'75')
  self.assertEqual(qualified_breaking_specs('Mitsubishi Electric','NF125-SV')['Icu tại 440 V AC (kA)'],'25')
  for model in ['NF250-HVU','NF250-HV [MB]','NF250-HV / NF250-SV']:
   self.assertEqual(qualified_breaking_specs('Mitsubishi Electric',model),{})
 def test_mitsubishi_main_poles_do_not_count_auxiliary_contacts(self):
  from app.services.reviewed_product_taxonomy import reviewed_price_row
  from app.services.catalog_product_sections import pole_compatible,coil_compatible
  row=reviewed_price_row({'brand':'Mitsubishi Electric','item_name':'S-T100 AC24V 2a2b','category':'CONTACTOR','specifications':{'Tiếp điểm phụ':'2a2b'}})
  device={'brand':'Mitsubishi Electric','type':'CONTACTOR','spec':{'so_cuc':'3P','Nguồn cuộn hút':'AC'}}
  self.assertTrue(pole_compatible(device,row));self.assertTrue(coil_compatible(device,row))
  self.assertFalse(coil_compatible(device,{**row,'item_name':'SD-T100 DC24V 2a2b'}))
  self.assertNotIn('Số cực',reviewed_price_row({**row,'item_name':'S-T100BC AC24V','specifications':{}})['specifications'])
 def test_1pn_notation_does_not_become_two_protected_poles(self):
  from app.services.catalog_family_matching import poles
  from app.services.catalog_product_sections import pole_compatible
  from app.services.reviewed_product_taxonomy import reviewed_price_row
  self.assertEqual(poles('BH-D6 1PN 16A'),'1P+N')
  self.assertIsNone(poles('SKU-D1PN16'))
  row=reviewed_price_row({'brand':'Mitsubishi Electric','item_name':'BV-DN 1PN 16A','category':'MCB','specifications':{}})
  self.assertEqual(row['category'],'RCBO')
  self.assertEqual(row['specifications']['Số cực'],'1P+N')
  self.assertTrue(pole_compatible({'spec':{'so_cuc':'1P+N'}},row))
  self.assertFalse(pole_compatible({'spec':{'so_cuc':'2P'}},row))
  from app.services.customer_technical_specs import qualified_breaking_specs
  self.assertEqual(qualified_breaking_specs('Mitsubishi Electric','BV-DN'),{'Icn tại 230 V AC (kA)':'4.5'})
  self.assertEqual(qualified_breaking_specs('Mitsubishi Electric','BV-DN6'),{'Icn tại 230 V AC (kA)':'6'})
  self.assertEqual(reviewed_price_row({**row,'item_name':'BV-DN6 1PN 16A','category':'MCB'})['category'],'RCBO')

 def test_reviewed_n_and_sq_families_keep_exact_model_boundary(self):
  from app.services.reviewed_product_taxonomy import reviewed_price_row
  for name in ['S-N150 AC200V 2a2b','SD-N300 DC24V 2a2b','S-T12SASQ AC200V','TH-N120KP 82A','TH-N400RH 250A','TH-N600KP 660A']:
   row=reviewed_price_row({'brand':'Mitsubishi Electric','item_name':name,'specifications':{}})
   self.assertEqual(row['specifications']['Số cực'],'3P',name)
  for name in ['S-N150BC AC200V','SD-N600 DC24V','TH-N400KPRH 250A','S-N600 AC200V']:
   row=reviewed_price_row({'brand':'Mitsubishi Electric','item_name':name,'specifications':{}})
   self.assertNotIn('Số cực',row['specifications'],name)

if __name__=='__main__':unittest.main()

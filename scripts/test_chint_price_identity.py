import copy,unittest
from app.services.chint_price_identity import normalize_nxr_row,normalize_nm8n125_row

class ChintPriceIdentityTests(unittest.TestCase):
 def setUp(self):
  self.registry={'source_url':'/vendor.pdf','source_sha256':'reviewed-pdf','pdf_page':52,'checked_at':'2026-10-23','items':{'837105':{'model':'NXR-25 0.1-0.16A','family':'NXR-25','setting_current_a':'0.1-0.16'}}}
  self.row={'id':'stable','brand':'CHINT','sku':'NXC-06~38','name':'NXC-06~38','item_name':'NXC-06~38','category':'CONTACTOR','price':327800,'source_sha256':'reviewed-pdf','source_page':52,'specifications':{'Mã hàng':'837105','In':'0.1-0.16A','Phù hợp':'NXC-06~38'},'columns':['Tên hàng','In','Phù hợp'],'cells':['NXC-06~38','0.1-0.16A','NXC-06~38']}
 def test_model_column_replaces_fitment_identity_preserving_price_and_raw_data(self):
  before=copy.deepcopy(self.row);out=normalize_nxr_row(self.row,self.registry)
  self.assertEqual(out['sku'],'NXR-25 0.1-0.16A');self.assertEqual(out['category'],'THERMAL_RELAY');self.assertEqual(out['price'],327800);self.assertEqual(out['id'],'stable')
  self.assertEqual(out['specifications']['Phù hợp'],'NXC-06~38');self.assertEqual(out['specifications']['Dải chỉnh định Ir (A)'],'0.1-0.16');self.assertNotIn('In',out['specifications']);self.assertEqual(self.row,before)
  self.assertEqual(normalize_nxr_row(out,self.registry),out)
 def test_documented_three_phase_configuration_is_added_without_changing_price(self):
  registry={**self.registry,'phase_evidence':{'pdf_page':1,'statement':'Three-phase bi-metal sheet type or electronic type'}}
  out=normalize_nxr_row(self.row,registry)
  self.assertEqual(out['specifications']['Số cực'],'3P')
  self.assertEqual(out['price'],self.row['price'])
  self.assertEqual(normalize_nxr_row(out,registry),out)
  from app.services.catalog_product_sections import pole_compatible
  self.assertTrue(pole_compatible({'display':'NXR-25 · 3P'},out))
  self.assertFalse(pole_compatible({'display':'Other · 2P'},out))
 def test_material_code_is_not_a_global_alias_across_regional_catalogs(self):
  for change in [{'source_sha256':'different-edition'},{'source_page':53},{'brand':'ABB'}]:
   row={**self.row,**change};self.assertEqual(normalize_nxr_row(row,self.registry),row)
 def test_conflicting_setting_range_is_rejected(self):
  row={**self.row,'specifications':{**self.row['specifications'],'In':'1-1.6A'}}
  with self.assertRaises(ValueError):normalize_nxr_row(row,self.registry)

class ChintNm8nRatingTests(unittest.TestCase):
 def setUp(self):
  self.registry={'source_sha256':'reviewed','nm8n125_rating_evidence':{'pdf_page':4,'scope':'reviewed AC table'}}
  self.row={'id':'stable','brand':'CHINT','sku':'NM8N-125C TM 125 1P','source_sha256':'reviewed','source_page':39,'price':123,'specifications':{'Số cực':'1P','Icu':'36kA','Ics':'100%'}}
 def test_single_pole_voltage_is_not_three_phase_voltage(self):
  out=normalize_nm8n125_row(self.row,self.registry)
  self.assertEqual(out['specifications']['Điện áp công bố Icu/Ics'],'220/230/240 V AC')
  self.assertEqual(out['price'],123);self.assertEqual(out['id'],'stable')
  self.assertEqual(normalize_nm8n125_row(out,self.registry),out)
  self.assertNotIn('Điện áp công bố Icu/Ics',self.row['specifications'])
 def test_four_c_order_code_uses_explicit_four_pole_rating(self):
  row={**self.row,'sku':'NM8N-125H TM 63 4C','source_page':42,'specifications':{'Số cực':'4P','Icu':'100kA','Ics':'100%'}}
  self.assertEqual(normalize_nm8n125_row(row,self.registry)['specifications']['Điện áp công bố Icu/Ics'],'380/400/415 V AC')
 def test_other_editions_frames_and_dc_are_not_enriched(self):
  for change in [{'source_sha256':'other'},{'source_page':43},{'brand':'ABB'},{'sku':'NM8N-250C TM 125 1P'},{'sku':'NM8N-125C TM 125 1P DC'}]:
   row={**self.row,**change};self.assertEqual(normalize_nm8n125_row(row,self.registry),row)
 def test_conflicting_breaking_capacity_is_rejected(self):
  row={**self.row,'specifications':{**self.row['specifications'],'Icu':'50kA'}}
  with self.assertRaises(ValueError):normalize_nm8n125_row(row,self.registry)
 def test_voltage_column_keeps_original_table_cells_aligned(self):
  row={**self.row,'columns':['Mã hàng','Giá'],'cells':[self.row['sku'],123]}
  out=normalize_nm8n125_row(row,self.registry)
  self.assertEqual(out['columns'],['Mã hàng','Giá','Điện áp công bố Icu/Ics'])
  self.assertEqual(out['cells'],[row['sku'],123,'220/230/240 V AC'])
  self.assertEqual(normalize_nm8n125_row(out,self.registry),out)

if __name__=='__main__':unittest.main()

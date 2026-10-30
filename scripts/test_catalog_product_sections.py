import unittest
from app.services.catalog_product_sections import candidate_rows,pole_compatible
from app.services.library_catalog_information import information_rows

class ProductSectionTests(unittest.TestCase):
    def test_ac_contactor_cad_excludes_dc_and_four_pole_prices(self):
        device={'brand':'LS','type':'CONTACTOR','product_code':'MC-32a',
                'spec':{'so_cuc':'3P','Loại cuộn hút':'AC'}}
        rows=[{'id':str(i),'brand':'LS','category':'CONTACTOR','sku':'MC-32a '+label,
               'price':100,'information_kind':'pricebook',
               'specifications':{'Số cực':pole,'Loại cuộn hút':coil}}
              for i,label,pole,coil in [(1,'AC','3P','AC'),(2,'DC','3P','DC'),(3,'4P','4P','AC')]]
        result=information_rows(device,rows)
        self.assertEqual([r['sku'] for r in result],['MC-32a AC'])

    def test_gmp_ct_suffix_is_not_a_main_pole_restriction(self):
        device={'brand':'LS','type':'RELAY','product_code':'GMP22-2P / GMP22-3P','display':'LS GMP22-2P / GMP22-3P','spec':{}}
        row={'sku':'GMP22-3P (1a1b)','specifications':{}}
        self.assertTrue(pole_compatible(device,row))
    def test_reviewed_explicit_accessory_rows_are_available_for_exact_cad_linking(self):
        device={'brand':'LS','type':'ACCESSORY','product_code':'COIL_12_ASM','spec':{},'catalog_references':{'source_row_scope':'explicit_only','row_links_reviewed':True,'options':[{'brand':'LS','model':'Coil for MC6a, 9a','source_row_id':'coil'}]}}
        row={'id':'coil','sku':'Coil for MC6a, 9a','brand':'LS','category':'ACCESSORY','specifications':{}}
        result=information_rows(device,[row,{**row,'id':'other'}])
        self.assertEqual([r['match_scope'] for r in result],['source_family'])
    def test_reviewed_row_list_still_cannot_override_wrong_poles(self):
        device={'brand':'LS','type':'MCCB','product_code':'FAMILY','spec':{'so_cuc':'3P'},'catalog_references':{'source_row_scope':'explicit_only','row_links_reviewed':True,'options':[{'brand':'LS','model':'OTHER','source_row_id':'wrong'}]}}
        row={'id':'wrong','sku':'OTHER','brand':'LS','category':'MCCB','specifications':{'Số cực':'4P'}}
        self.assertFalse(any(r['match_scope']=='source_family' for r in information_rows(device,[row])))

    def device(self):return {'brand':'LS Electric','type':'MCB','product_code':'BKN','spec':{'so_cuc':'4P'}}
    def row(self,brand='LS Electric',pole='4P',sku='BKN-C20'):
        return {'id':brand+sku+pole,'brand':brand,'category':'MCB','sku':sku,'specifications':{'Số cực':pole,'In (A)':'20'},'price':None}
    def test_four_poles_never_include_other_or_unknown_configurations(self):
        device=self.device()
        for pole in ('1P','2P','3P','3P+N','1P / 4P',''):
            self.assertFalse(pole_compatible(device,self.row(pole=pole)))
        self.assertTrue(pole_compatible(device,self.row()))
        self.assertEqual(len(candidate_rows(device,[self.row(),self.row(pole='3P')],False)),1)
    def test_sections_select_correct_brand_and_function(self):
        rows=[self.row(),self.row(brand='ABB'),{**self.row(brand='CHINT'),'category':'MCCB'}]
        self.assertEqual([r['brand'] for r in candidate_rows(self.device(),rows,False)],['LS Electric'])
        self.assertEqual([r['brand'] for r in candidate_rows(self.device(),rows,True)],['ABB'])
    def test_current_family_and_explicit_references_also_obey_poles(self):
        device=self.device();device['catalog_references']={'options':[{'brand':'LS Electric','model':'BKN-3P','specifications':{'Số cực':'3P'}}]}
        rows=information_rows(device,[self.row(),self.row(pole='3P')])
        self.assertTrue(rows)
        self.assertTrue(all(pole_compatible(device,r) for r in rows))
    def test_unknown_poles_do_not_generate_breaker_replacement_claims(self):
        device=self.device();device['spec']={}
        self.assertEqual(candidate_rows(device,[self.row(brand='ABB')],True),[])
    def test_text_only_ratings_do_not_crash_candidate_selection(self):
        device=self.device();device['spec'].update(kha_nang_cat='Theo catalog',dong_dinh_muc='Chọn biến thể')
        row=self.row(brand='ABB');row['specifications']['Icu (kA)']='6'
        self.assertEqual(len(candidate_rows(device,[row],True)),1)
    def test_matching_function_alone_does_not_claim_replacement_fit(self):
        device={'brand':'LS Electric','type':'CONTACTOR','spec':{}}
        row={'id':'x','brand':'ABB','category':'CONTACTOR','sku':'AF','specifications':{}}
        self.assertEqual(candidate_rows(device,[row],True),[])
    def test_five_pole_accessories_keep_their_pole_count(self):
        device={'spec':{'so_cuc':'5P'}}
        self.assertTrue(pole_compatible(device,self.row(pole='5P')))
        self.assertFalse(pole_compatible(device,self.row(pole='4P')))
    def test_ac_and_dc_are_not_interchangeable_at_same_numeric_voltage(self):
        device=self.device();device['spec']['dien_ap_dinh_muc']='230 VAC'
        row=self.row(brand='ABB');row['specifications']['Điện áp định mức']='230 VDC'
        self.assertEqual(candidate_rows(device,[row],True),[])
    def test_required_leakage_sensitivity_cannot_be_missing_or_different(self):
        device=self.device();device['type']='RCBO';device['spec']['dong_ro_mA']='30'
        row={**self.row(brand='ABB'),'category':'RCBO'}
        self.assertEqual(candidate_rows(device,[row],True),[])
        row['specifications']['Dòng rò (mA)']='300'
        self.assertEqual(candidate_rows(device,[row],True),[])
        row['specifications']['Dòng rò (mA)']='30'
        self.assertEqual(len(candidate_rows(device,[row],True)),1)

if __name__=='__main__':unittest.main()

import unittest
from app.services.catalog_product_sections import candidate_rows,pole_compatible
from app.services.library_catalog_information import information_rows

class ProductSectionTests(unittest.TestCase):
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

if __name__=='__main__':unittest.main()

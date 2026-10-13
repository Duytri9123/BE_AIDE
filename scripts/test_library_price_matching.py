import unittest
from app.services.library_price_matching import configuration_links


class LibraryPriceMatchingTests(unittest.TestCase):
    def device(self, **changes):
        return {**dict(id='TB-A2',brand='ABB',brand_identification_status='verified',
                       type='MCCB',product_code='A2',spec={'so_cuc':'2P'}), **changes}

    def row(self, **changes):
        return {**dict(id='price-A2',brand='ABB',category='MCCB',item_name='A2 2P 100A',
                       sku='ORDER-A2',price=100,specifications={'Số cực':'2P','In (A)':'100'}), **changes}

    def test_same_brand_different_type_model_or_poles_never_match(self):
        wrong = [self.row(id='MCB',category='MCB'), self.row(id='A1',item_name='A1 2P 100A'),
                 self.row(id='3P',item_name='A2 3P 100A',specifications={'Số cực':'3P','In (A)':'100'}),
                 self.row(id='maker',brand='CHINT')]
        self.assertEqual(configuration_links(self.device(),wrong),{})
        self.assertEqual(configuration_links(self.device(),[self.row(),*wrong]),{'price-A2':'TB-A2'})

    def test_all_matching_prices_remain_available_for_pagination(self):
        rows=[self.row(id=str(i),item_name=f'A2 2P {i+1}A',specifications={'Số cực':'2P','In (A)':str(i+1)}) for i in range(65)]
        self.assertEqual(len(configuration_links(self.device(),rows)),65)

    def test_unknown_brand_identity_missing_code_or_poles_stays_empty(self):
        for device in [self.device(brand_identification_status='unknown'),self.device(product_code=None),self.device(spec={})]:
            self.assertEqual(configuration_links(device,[self.row()]),{})

    def test_shared_contactor_models_and_main_poles(self):
        device=self.device(type='Contactor',product_code='MC-6a / 9a / 12a',spec={'so_cuc_chinh':3})
        rows=[self.row(id=model,category='CONTACTOR',item_name=model+' (2)',sku=model,
                       group='CONTACTOR 3 POLES',specifications={}) for model in ['MC-6a','MC-9a','MC-12a','MC-18a']]
        self.assertEqual(set(configuration_links(device,rows)),{'MC-6a','MC-9a','MC-12a'})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc_chinh':4}},rows),{})

    def test_slash_is_part_of_four_pole_model_identity(self):
        device=self.device(type='Contactor',product_code='MC-6a/4 / 9a/4',spec={'so_cuc_chinh':4})
        row=self.row(category='CONTACTOR',item_name='MC-9a/4 (2)',group='CONTACTOR 4 POLES',specifications={})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})


if __name__=='__main__':
    unittest.main()

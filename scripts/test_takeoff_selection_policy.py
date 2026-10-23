import unittest
from unittest.mock import patch
from app.services.library_review_scope import preferred_brand_for_device
from app.services.ai.takeoff_pricebook import match_device
from app.services.cad.automatic_selection import select_device_geometry


class SelectionPolicyTests(unittest.TestCase):
    def test_literal_breaking_requirement_filters_ls_price_rows(self):
        rows=[dict(id=str(ka),category='MCCB',brand='LS',item_name='ABN103c',sku='ABN103c',
                   price=ka*100,specifications={'Số cực':'3P','In (A)':'100A','Icu(KA)':str(ka)})
              for ka in (18,35,50)]
        result=match_device({'category':'MCCB','brand':'LS','spec':'3P 100A 35kA'},rows)
        self.assertEqual([x['price'] for x in result['candidates']],[3500,5000])

    def test_auxiliary_voltage_and_current_type_precede_price(self):
        rows=[dict(id=str(i),category='LIGHT',brand=brand,item_name='Lamp '+voltage,
                   sku=str(i),price=price,specifications={'Voltage':voltage})
              for i,brand,voltage,price in [(1,'LS','110VAC',10),(2,'CHINT','220VDC',20),
                                          (3,'LS','220VAC',100),(4,'CHINT','220VAC',40)]]
        result=match_device({'category':'LIGHT','brand':'LS','selection_source':'default_brand',
                             'spec':'220VAC'},rows)
        self.assertEqual([x['price'] for x in result['candidates']],[40,100])

    def test_main_device_does_not_fall_back_to_another_manufacturer(self):
        with patch('app.services.cad.automatic_selection.candidates', return_value=[]) as lookup:
            result=select_device_geometry({'category':'MCCB','brand':'LS',
                'spec':'3P 100A 35kA','selection_source':'default_brand'})
        self.assertEqual(lookup.call_count,1)
        self.assertEqual(result['brand'],'LS')
        self.assertFalse(result['cad'].get('asset_id'))

    def test_project_brand_only_applies_to_main_or_dependent_devices(self):
        self.assertEqual(preferred_brand_for_device({'category':'MCCB'}, 'ABB'), 'ABB')
        self.assertIsNone(preferred_brand_for_device({'category':'LIGHT', 'brand':'ABB', 'selection_source':'default_brand'}, 'ABB'))
        self.assertEqual(preferred_brand_for_device({'category':'LIGHT', 'detected_brand':'Schneider'}, 'ABB'), 'Schneider')
        self.assertEqual(preferred_brand_for_device({'category':'AUX_CONTACT'}, 'ABB'), 'ABB')

    def test_optional_candidates_are_sorted_by_positive_price_across_brands(self):
        rows=[dict(id=str(i),category='LIGHT',brand=brand,item_name='Lamp',sku=str(i),price=price,specifications={})
              for i,brand,price in [(1,'ABB',100),(2,'CHINT',40),(3,'ABB',None),(4,'CHINT',0)]]
        result=match_device({'category':'LIGHT','brand':'ABB','selection_source':'default_brand'},rows)
        self.assertEqual(result['candidates'][0]['price'],40)
        self.assertEqual(result['candidate_count'],4)
        self.assertEqual(result['status'],'needs_selection')

    def test_geometry_cannot_use_highest_of_multiple_breaking_ratings(self):
        asset=dict(id='test',name='XT1',search_aliases=[],specifications={'dong_dinh_muc':'100','kha_nang_cat':'18 kA / 36 kA'},electrical_variants=[])
        with patch('app.services.cad.automatic_selection.candidates',return_value=[asset]):
            result=select_device_geometry({'category':'MCCB','spec':'3P 100A 25kA','selection_source':'unspecified_brand'})
        self.assertEqual(result['cad']['automatic_selection']['status'],'unresolved')
        self.assertIn('Khả năng cắt',result['cad']['automatic_selection']['rejected'][0]['reason'])


if __name__ == '__main__':
    unittest.main()

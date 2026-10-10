import unittest
from types import SimpleNamespace
from app.services.ai.manufacturer_information import product_information, compact_summary


class ProductInformationTests(unittest.TestCase):
    def test_summary_keeps_complete_facts_and_units(self):
        summary=compact_summary('Overview:\n* Voltage: 220 V AC\n* Current: 30 A\n* ' + 'x'*200)
        self.assertEqual(summary,'Voltage: 220 V AC\nCurrent: 30 A')
    def engine(self):
        return SimpleNamespace(reference_profiles=[
            dict(category='MCB',name='Chint X100',brand='Chint',series='X100',poles=2,reference_path='chint'),
            dict(category='MCB',name='Other X100',brand='Other',series='X100',poles=2,reference_path='other'),
            dict(category='MCB',name='Chint X1000',brand='Chint',series='X1000',poles=2,reference_path='prefix')])

    def test_same_model_different_brand_is_not_same_brand_match(self):
        result=product_information(dict(category='MCB',brand='CHINT',part_number='X100',poles=2),self.engine())
        self.assertEqual([r['brand_match'] for r in result['system_matches']],['same','different'])
        self.assertTrue(all(not r['fabrication_ready'] for r in result['system_matches']))

    def test_unknown_brand_is_asian_without_manufacturer_confirmation(self):
        result=product_information(dict(category='MCB',brand='',part_number='X100'),self.engine())
        self.assertEqual(result['brand'],'Asian')
        self.assertTrue(all(r['brand_match']=='unknown' for r in result['system_matches']))

    def test_related_model_and_wrong_poles_are_not_exact(self):
        result=product_information(dict(category='MCB',brand='Chint',part_number='X100',poles=3),self.engine())
        self.assertEqual(result['system_matches'],[])
        self.assertEqual(result['match_status'],'model_not_verified')

    def test_only_safe_web_links_and_no_synthetic_web_claim(self):
        result=product_information(dict(category='MCB'),self.engine(),{'success':True,'results':[
            {'url':'javascript:alert(1)'},{'url':'https://example.com/datasheet','title':'Sheet','snippet':'x'*999}]})
        self.assertEqual(len(result['sources']),1)
        self.assertEqual(len(result['sources'][0]['snippet']),250)
        self.assertEqual(result['match_status'],'model_unspecified')

    def test_dealer_is_not_manufacturer_information(self):
        result=product_information(dict(category='MCB',brand='LS'),self.engine(),{'success':True,'results':[
            {'url':'https://dealer.example/item','title':'Official LS'},
            {'url':'https://www.lselectric.com/product','title':'LS'}]})
        self.assertEqual(len(result['sources']),1)
        self.assertEqual(result['sources'][0]['source_type'],'manufacturer')

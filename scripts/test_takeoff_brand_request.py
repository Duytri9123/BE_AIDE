import unittest
from copy import deepcopy
from unittest.mock import patch
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.takeoff_brand_request import apply_takeoff_brand, requested_brand_candidates
from app.services.library_review_scope import preferred_brand_for_device
from app.services.ai.takeoff_pricebook import link_devices
from app.services.cad.automatic_selection import select_device_geometry


class TakeoffBrandRequestTests(unittest.TestCase):
    def device(self, **changes):
        return Device(**(dict(category='MCCB', name='MCCB tổng', spec='3P 100A 25kA',
            poles=3, in_a=100, icu_ka=25, quantity=1, panel_code='MDB101',
            brand='Schneider', part_number='SOURCE-CODE', tag='QF1',
            box_2d=[10, 10, 50, 50], evidence_image='source.png') | changes))

    def test_chint_is_applied_during_takeoff_without_rewriting_source(self):
        d = self.device(selected_product={'brand':'Schneider','sku':'SOURCE-CODE'},
                        pricebook_match={'status':'matched','price_row_id':'old'})
        before = d.model_dump()
        self.assertTrue(apply_takeoff_brand(d, 'CHINT'))
        self.assertEqual((d.brand, d.detected_brand, d.selection_source), ('CHINT','Schneider','user_request'))
        self.assertEqual(d.part_number, '')
        self.assertIsNone(d.selected_product)
        self.assertIsNone(d.pricebook_match)
        self.assertEqual(d.source_observations['schematic']['part_number'], 'SOURCE-CODE')
        for field in ('spec','poles','in_a','icu_ka','quantity','tag','panel_code','box_2d','evidence_image'):
            self.assertEqual(getattr(d,field), before[field], field)
        self.assertEqual(preferred_brand_for_device(d, 'ABB'), 'CHINT')
        source = deepcopy(d.source_observations)
        apply_takeoff_brand(d, 'CHINT')
        self.assertEqual(d.source_observations, source)

    def test_unspecified_brand_and_existing_chint_model(self):
        d = self.device(brand='', part_number='')
        apply_takeoff_brand(d, 'CHINT')
        self.assertEqual(d.brand, 'CHINT')
        self.assertEqual(d.detected_brand, '')
        d = self.device(brand='CHINT', part_number='EXACT')
        apply_takeoff_brand(d, 'CHINT')
        self.assertEqual(d.part_number, 'EXACT')

    def test_auxiliary_items_keep_their_own_identity(self):
        for kind in ('CT','LIGHT','FUSE','VOLTMETER'):
            d = self.device(category=kind, brand='Asian')
            before = d.model_dump()
            self.assertFalse(apply_takeoff_brand(d, 'CHINT'))
            self.assertEqual(d.model_dump(), before)

    def test_only_dependent_accessories_follow_parent(self):
        d = self.device(accompanying_accessories=[
            dict(category='SHUNT_TRIP',brand='Schneider',sku='OLD-AUX',spec='24V',quantity=1),
            dict(category='LIGHT',brand='Asian',spec='220V',quantity=3)])
        apply_takeoff_brand(d, 'CHINT')
        child, lamp = d.accompanying_accessories
        self.assertEqual((child['brand'],child['sku'],child['spec']), ('CHINT','','24V'))
        self.assertEqual(child['source_observations']['schematic']['part_number'], 'OLD-AUX')
        self.assertEqual(lamp['brand'], 'Asian')

    def test_pricebook_and_cad_use_requested_brand_not_source_manufacturer(self):
        d = self.device()
        apply_takeoff_brand(d, 'CHINT')
        rows = [dict(id=brand,brand=brand,category='MCCB',item_name='Breaker '+brand,
                     sku=brand,price=100,specifications={'Số cực':'3P','In (A)':'100','Icu(KA)':'25'})
                for brand in ('CHINT','Schneider')]
        link_devices([d], rows)
        self.assertEqual({c['brand'] for c in d.pricebook_match['candidates']}, {'CHINT'})
        self.assertNotEqual(d.pricebook_match['status'], 'matched')
        filtered = requested_brand_candidates({'CHINT':[1],'Schneider':[2]}, d.brand)
        self.assertEqual(filtered, {'CHINT':[1]})
        with patch('app.services.cad.automatic_selection.candidates', return_value=[]) as lookup:
            select_device_geometry(d.model_dump())
        self.assertEqual(lookup.call_args.args[1], 'CHINT')

    def test_no_requirement_leaves_source_alone(self):
        d = self.device()
        before = d.model_dump()
        self.assertFalse(apply_takeoff_brand(d, None))
        self.assertEqual(d.model_dump(), before)


if __name__ == '__main__':
    unittest.main()

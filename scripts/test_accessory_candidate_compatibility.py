import unittest
from types import SimpleNamespace
from app.services.ai.takeoff_scope import compatible_accessory_candidates

class CompatibilityTests(unittest.TestCase):
    def parent(self, brand=''):
        return SimpleNamespace(brand=brand, selected_product=None, catalog_candidates={
            'LS Electric': [{'sku':'TS250H','parameters':{'frame_a':250}}]})

    def test_requested_brand_applies_before_parent_sku_is_selected(self):
        result=compatible_accessory_candidates(self.parent(), {
            'LS Electric':[{'sku':'SHT','parameters':{'frame_a':250}}],
            'Schneider Electric':[{'sku':'MX'}]}, 'LS Electric')
        self.assertEqual(set(result), {'LS Electric'})

    def test_known_wrong_frame_is_rejected(self):
        self.assertEqual(compatible_accessory_candidates(self.parent(), {
            'LS Electric':[{'sku':'SHT400','parameters':{'frame_a':400}}]}, 'LS Electric'), {})

    def test_unknown_frame_stays_unverified(self):
        result=compatible_accessory_candidates(self.parent(), {'LS':[{'sku':'SHT'}]}, 'LS Electric')
        self.assertEqual(result, {'LS':[{'sku':'SHT'}]})

    def test_selected_parent_brand_takes_precedence(self):
        self.assertEqual(compatible_accessory_candidates(self.parent('LS Electric'), {
            'ABB':[{'sku':'SHT'}]}, 'ABB'), {})

    def test_same_frame_does_not_make_another_breaker_family_compatible(self):
        self.assertEqual(compatible_accessory_candidates(self.parent(), {
            'LS Electric':[{'sku':'SHT','parameters':{'frame_a':250},
                'technical_evidence':'Dùng cho ABN100c đến ABH250c'}]}, 'LS Electric'), {})

if __name__ == '__main__': unittest.main()

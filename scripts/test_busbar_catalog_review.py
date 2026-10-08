import unittest,json
from app.services.cad.busbar_catalog_review import review,PATH
class BusbarTests(unittest.TestCase):
 def test_estimates_are_not_verified_ratings(self):
  items=json.loads(PATH.read_text(encoding='utf8'))['busbar']['items']
  self.assertEqual(len(items),84)
  for b in items:
   self.assertEqual(b['section_mm2'],b['width_mm']*b['thickness_mm'])
   self.assertIsNone(b['I_rated'])
   self.assertGreater(b['I_estimated'],0)
 def test_proposal_keeps_current_and_length_unverified(self):
  r=review(200,555)
  self.assertIsNotNone(r['selected'])
  self.assertGreaterEqual(r['selected']['I_estimated'],200)
  self.assertFalse(r['release_ready'])
  self.assertFalse(r['stock_length_is_route_length'])

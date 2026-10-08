import unittest
from app.services.cad.design_policy import dimensions_for_current,check_fishbone
class PolicyTests(unittest.TestCase):
 def test_boundaries(self):
  self.assertEqual([dimensions_for_current(a)['top_gap_mm'] for a in [100,199,200,250,299,300,400]],[150,150,300,300,300,400,400])
  self.assertEqual(dimensions_for_current(200)['side_margin_mm'],110)
  self.assertEqual(dimensions_for_current(201)['side_margin_mm'],150)
  self.assertIsNone(dimensions_for_current(63)['top_gap_mm'])
 def test_fishbone_limit(self):
  check_fishbone(250)
  with self.assertRaises(ValueError):check_fishbone(251)

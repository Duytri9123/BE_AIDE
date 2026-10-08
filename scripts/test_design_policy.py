import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.services.cad import design_policy
from app.services.cad.design_policy import dimensions_for_current,check_fishbone
class PolicyTests(unittest.TestCase):
 def test_json_variables_change_output_without_code_change(self):
  rules=json.loads(design_policy.RULES_PATH.read_text(encoding='utf8'))
  rules['design_variables'].update(d2=275,d4=160)
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'rules.json'
   path.write_text(json.dumps(rules),encoding='utf8')
   with patch.object(design_policy,'RULES_PATH',path):
    result=dimensions_for_current(250)
    self.assertEqual(result['top_gap_mm'],275)
    self.assertEqual(result['side_margin_mm'],160)
    self.assertEqual(result['top_gap_variable'],'d2')
 def test_boundaries(self):
  self.assertEqual([dimensions_for_current(a)['top_gap_mm'] for a in [100,199,200,250,299,300,400]],[150,150,250,250,250,400,400])
  self.assertEqual(dimensions_for_current(200)['side_margin_mm'],110)
  self.assertEqual(dimensions_for_current(201)['side_margin_mm'],150)
  self.assertIsNone(dimensions_for_current(63)['top_gap_mm'])
 def test_fishbone_limit(self):
  check_fishbone(250)
  with self.assertRaises(ValueError):check_fishbone(251)

 def test_cable_envelope_increases_only_when_required(self):
  c=dict(outer_diameter_mm=25,minimum_inner_bend_radius_mm=150,lug_straight_mm=40,terminal_offset_mm=0,installation_allowance_mm=20,manufacturer_source='test-datasheet',bend_angle_deg=90)
  self.assertEqual(dimensions_for_current(200,c)['top_gap_mm'],250)
  c['minimum_inner_bend_radius_mm']=220
  self.assertEqual(dimensions_for_current(200,c)['top_gap_mm'],305)
  self.assertFalse(dimensions_for_current(200)['cable_space_verified'])

import unittest
from types import SimpleNamespace
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.takeoff_scope import apply_requested_accessories,validate_file_plan
from app.services.ai.cluster_equipment_service import AccompanyingEquipmentService
class ScopeAccessoriesTests(unittest.TestCase):
 def test_request_accessory_has_parent_and_survives_normalization(self):
  parent=ExtractedDeviceSchema(category='MCCB',name='MCCB',spec='3P 200A 85kA',tag='Q1',brand='LS',quantity=1)
  apply_requested_accessories([parent],{'accessories':[{'parent_id':0,'basis':'user_request','request_quote':'thêm shunt trip cho Q1','category':'SHUNT_TRIP','name':'Cuộn cắt','quantity':1}]},'Hãy thêm shunt trip cho Q1')
  result=AccompanyingEquipmentService.format_accessories(parent.accompanying_accessories)
  self.assertEqual(result[0]['brand'],'LS');self.assertEqual(result[0]['parent_tag'],'Q1')
  self.assertTrue(result[0]['not_drawn']);self.assertTrue(result[0]['requires_same_brand'])
 def test_negative_request_does_not_add_shunt(self):
  parent=ExtractedDeviceSchema(category='MCCB',name='MCCB',spec='3P 200A')
  apply_requested_accessories([parent],{'accessories':[{'parent_id':0,'basis':'user_request','request_quote':'thêm shunt trip','category':'SHUNT_TRIP','name':'Cuộn cắt'}]},'Không thêm shunt trip')
  self.assertFalse(parent.accompanying_accessories)
 def test_unrequested_accessory_is_not_inserted(self):
  parent=ExtractedDeviceSchema(category='MCCB',name='MCCB',spec='3P 200A 85kA')
  apply_requested_accessories([parent],{'accessories':[{'parent_id':0,'basis':'user_request','request_quote':'thêm shunt trip','category':'SHUNT_TRIP','name':'Cuộn cắt'}]},'Giữ nguyên bản vẽ')
  self.assertFalse(parent.accompanying_accessories)
 def test_multifile_plan_requires_all_files_and_valid_ids(self):
  files=[SimpleNamespace(id=1,filename='sld.pdf'),SimpleNamespace(id=2,filename='requirements.xlsx')]
  plan=validate_file_plan({'files':[{'file_id':1,'extract':True},{'file_id':2,'extract':False}]},files)
  self.assertEqual([r['file_id'] for r in plan if r['extract']],[1])
  with self.assertRaises(ValueError):validate_file_plan({'files':[{'file_id':1,'extract':True}]},files)
  with self.assertRaises(ValueError):validate_file_plan({'files':[{'file_id':1,'extract':True},{'file_id':999,'extract':False}]},files)

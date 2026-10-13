import json,unittest
from unittest.mock import AsyncMock,patch
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.takeoff_device_assessment import assess_takeoff_devices
class BatchAssessmentTests(unittest.IsolatedAsyncioTestCase):
 async def test_assessment_preserves_source_and_receives_requirement(self):
  device=ExtractedDeviceSchema(category='VOLTMETER',name='Vôn kế',spec='0-600V')
  answer=json.dumps({'devices':[{'id':0,'symbol_interpretation':'Chưa có ảnh','function':'Đo điện áp','assessment':'Cần biết điện áp thực tế','suitable_product':'Vôn kế 0-600V','alternatives':[],'missing_information':[]}]})
  with patch('app.services.ai.takeoff_device_assessment.ConnectionPoolService.call_with_fallback',new_callable=AsyncMock,return_value=(answer,None)) as call:
   self.assertEqual(await assess_takeoff_devices([device],[],None,'Ưu tiên LS, giữ nguyên thang đo'),1)
   self.assertIn('Ưu tiên LS',call.call_args.kwargs['prompt'])
  self.assertEqual(device.spec,'0-600V')
  self.assertEqual(device.device_assessment['function'],'Đo điện áp')
 async def test_incomplete_batch_cannot_report_complete(self):
  device=ExtractedDeviceSchema(category='VOLTMETER',name='Vôn kế',spec='0-600V')
  with patch('app.services.ai.takeoff_device_assessment.ConnectionPoolService.call_with_fallback',new_callable=AsyncMock,return_value=('{"devices":[]}',None)):
   with self.assertRaises(ValueError):await assess_takeoff_devices([device],[],None)
 async def test_blank_assessment_cannot_report_complete(self):
  device=ExtractedDeviceSchema(category='VOLTMETER',name='Vôn kế',spec='0-600V')
  answer='{"devices":[{"id":0,"function":" ","assessment":"N/A","suitable_product":" "}]}'
  with patch('app.services.ai.takeoff_device_assessment.ConnectionPoolService.call_with_fallback',new_callable=AsyncMock,return_value=(answer,None)):
   with self.assertRaises(ValueError):await assess_takeoff_devices([device],[],None)

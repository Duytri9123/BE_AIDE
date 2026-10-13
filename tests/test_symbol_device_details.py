import unittest,json
from app.services.ai.device_details import parse_details
class DetailsTests(unittest.TestCase):
 def test_structured_vision_response_becomes_readable_text(self):
  result=parse_details(json.dumps({'symbol_interpretation':'V trong vòng tròn','function':{'role':'Đo điện áp'},'assessment':'Cần đối chiếu điện áp đo','suitable_product':{'type':'Vôn kế','poles':'Không áp dụng'},'alternatives':[{'option':'Đồng hồ đa năng','condition':'Kiểm tra nguồn nuôi và đấu dây'}]},ensure_ascii=False))
  self.assertEqual(result['function'],'Đo điện áp')
  self.assertEqual(result['suitable_product'],'Vôn kế')
  self.assertIn('Kiểm tra nguồn nuôi',result['alternatives'][0])

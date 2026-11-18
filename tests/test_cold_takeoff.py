import tempfile,unittest
from pathlib import Path
from unittest.mock import AsyncMock,patch
from PIL import Image
import ezdxf

class ColdRunTests(unittest.IsolatedAsyncioTestCase):
 async def test_failed_region_cancels_peers_before_removing_images(self):
  import asyncio,json
  from app.services.ai.regional_takeoff import extract_regions
  started=asyncio.Event();cancelled=[]
  async def call(path,prompt):
   name=Path(path).stem
   if name=='source':return json.dumps({'regions':[{'box_2d':[0,0,500,500]},{'box_2d':[500,500,1000,1000]}]})
   if name=='0':
    await started.wait()
    raise RuntimeError('provider unavailable')
   started.set()
   try:await asyncio.Event().wait()
   finally:cancelled.append(Path(path).is_file())
  with tempfile.TemporaryDirectory() as folder:
   image=Path(folder)/'source.png';Image.new('RGB',(100,100),'white').save(image)
   with self.assertRaisesRegex(RuntimeError,'provider unavailable'):
    await extract_regions(image,'read',call,concurrency=2)
  self.assertEqual(cancelled,[True])

 async def test_capacity_retry_keeps_exact_configured_model(self):
  from types import SimpleNamespace
  from unittest.mock import MagicMock
  from app.services.ai.connection_pool import ConnectionPoolService
  from app.core.exceptions import AIVisionError
  conn=SimpleNamespace(id=1,provider='antigravity',selected_model='ag/gemini-3.8-flash-high',name='test',priority=1,quotas={},api_key='test')
  db=MagicMock();result=MagicMock();result.scalars.return_value.all.return_value=[];db.execute=AsyncMock(return_value=result)
  call=AsyncMock(side_effect=[AIVisionError('503 MODEL_CAPACITY_EXHAUSTED',{}),'fresh'])
  with patch('app.services.ai.connection_pool.TokenRefreshService.get_active_token',new=AsyncMock(return_value='test')),patch('app.services.ai.connection_pool.asyncio.sleep',new=AsyncMock()):
   response,_=await ConnectionPoolService.call_with_fallback(db,[conn],call)
  self.assertEqual(response,'fresh')
  self.assertEqual([c.kwargs['model'] for c in call.await_args_list],[conn.selected_model]*2)

 async def test_disabled_vision_cache_neither_reads_nor_writes(self):
  from app.services.ai.vision_analyzer import VisionAnalyzerService,cache_service
  with tempfile.TemporaryDirectory() as folder:
   image=Path(folder)/'source.png';Image.new('RGB',(50,50),'white').save(image)
   with patch.dict('os.environ',{'ELQUOTE_AI_CACHE_ENABLED':'0'}),patch.object(cache_service,'get',new=AsyncMock()) as read,patch.object(cache_service,'set',new=AsyncMock()) as write,patch.object(VisionAnalyzerService,'_call_openai',new=AsyncMock(return_value='Fresh model response longer than twenty characters')) as call:
    result=await VisionAnalyzerService.analyze_image(str(image),'read source','openai','test','test-model')
    self.assertIn('Fresh',result);call.assert_awaited_once();read.assert_not_awaited();write.assert_not_awaited()

 def test_control_boxes_keep_whole_adjacent_rectangles(self):
  from app.services.ai.cad_branch_evidence import seed_control_label_boxes
  from app.services.ingestion.cad_source_evidence import cad_evidence,region_world
  doc=ezdxf.new();m=doc.modelspace()
  m.add_text('MDB',dxfattribs={'insert':(-30,60),'height':10})
  m.add_text('SOURCE',dxfattribs={'insert':(150,-30),'height':10})
  m.add_lwpolyline([(0,0),(80,0),(80,25),(0,25)],close=True)
  m.add_lwpolyline([(80,0),(120,0),(120,25),(80,25)],close=True)
  m.add_text('Contactor',dxfattribs={'insert':(5,5),'height':10})
  m.add_text('24H',dxfattribs={'insert':(85,5),'height':10})
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'controls.dxf';doc.saveas(path)
   result=seed_control_label_boxes(path,[0,0,1,1],[{'name':'Contactor'},{'name':'Bộ hẹn giờ 24H'}],[])
   self.assertEqual(len(result),2)
   for row in result:self.assertEqual(row['geometry_source'],'native_cad_control_rectangle')
   self.assertNotEqual(result[0]['symbol_box_2d'],result[1]['symbol_box_2d'])
   self.assertEqual(result[0]['group_reference_box_2d'],result[1]['group_reference_box_2d'])

if __name__=='__main__':unittest.main()

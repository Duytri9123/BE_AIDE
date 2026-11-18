import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from PIL import Image
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.takeoff_evidence_completion import complete_evidence,evidence_gaps
from app.services.ai.evidence_crops import apply_verified_boxes
from app.services.ai.evidence_preview import device_preview
from app.services.ai.takeoff_catalog import suggest_takeoff_products
from app.services.ai.el_input_context import input_context

class EvidenceCompletionTests(unittest.IsolatedAsyncioTestCase):
 async def test_missing_branch_tag_and_load_are_recovered_then_independently_checked(self):
  d=ExtractedDeviceSchema(category='MCB',name='MCB',spec='1P 10A 6kA',tag='L4',connected_load='Chiếu sáng')
  box={'device_id':'0','verified':True,'symbol_verified':True,'symbol_box_2d':[100,100,150,150],
       'text_box_2d':[150,100,180,200],'tag_box_2d':[180,100,200,150],
       'load_box_2d':[400,100,500,200],'load_label':'CHIẾU SÁNG','relationship_evidence':'Dây L4 nối xuống nhãn tải'}
  check={'device_id':'0','matches':True,'symbol_complete':True,'label_complete':True,'isolated':True,
         'tag_matches':True,'load_matches':True,'relationship_verified':True,'observed':'L4 MCB 1P 10A 6kA'}
  call=AsyncMock(side_effect=[json.dumps({'boxes':[box]}),json.dumps({'checks':[check]})])
  image=Image.new('RGB',(1000,1000),'white')
  # Distinct source ink is needed: identical blank crops are intentionally deduplicated.
  image.paste('black',(110,110,140,140))
  image.paste('blue',(110,410,140,440))
  result=await complete_evidence(image,'source.png',[d],{'boxes':[]},call)
  self.assertEqual(call.await_count,2)
  self.assertEqual(evidence_gaps(d,result['boxes'][0]),[])
  apply_verified_boxes([d],result,require_symbols=True)
  self.assertTrue(d.evidence_region['tag_verified'])
  self.assertTrue(d.evidence_region['load_verified'])
  images=device_preview(image,d.evidence_region,tight=True)
  self.assertEqual([i['kind'] for i in images],['device','load','relationship'])
  self.assertIn('CHIẾU SÁNG',images[1]['label'])

 async def test_group_audit_receives_the_declared_material_quantity(self):
  from app.services.ai.device_crop_audit import audit_device_previews
  d=ExtractedDeviceSchema(category='METER',name='Ampe kế',spec='A',quantity=3)
  box={'device_id':'0','verified':True,'symbol_verified':True,
       'symbol_box_2d':[100,100,200,300],'text_box_2d':[200,100,220,300]}
  call=AsyncMock(return_value=json.dumps({'checks':[{'device_id':'0','matches':True,
       'symbol_complete':True,'label_complete':True,'isolated':True}]}))
  result=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,[d],{'boxes':[box]})
  self.assertEqual(json.loads(call.await_args.args[1].rsplit('\n',1)[-1])[0]['quantity'],3)
  self.assertTrue(result['boxes'][0]['verified'])

 async def test_false_load_relationship_remains_unproven(self):
  d=ExtractedDeviceSchema(category='MCB',name='MCB',spec='',tag='L4',connected_load='Chiếu sáng')
  call=AsyncMock(return_value=json.dumps({'boxes':[]}))
  result=await complete_evidence(Image.new('RGB',(100,100)),'source.png',[d],{'boxes':[]},call)
  self.assertEqual(call.await_count,1)  # Identical missing evidence must not trigger the same reread again.
  self.assertEqual(len(evidence_gaps(d,None)),3)
  self.assertEqual(result['boxes'],[])

 def test_context_uses_current_request_and_scope_as_separate_data(self):
  ctx=input_context('hi',{'file_ids':[7],'iteration_id':4,'messages':[{'role':'user','content':'bóc tất cả'}]},'conversation',[])
  self.assertEqual(ctx['intent'],'conversation')
  self.assertEqual(ctx['current_request'],'hi')
  self.assertEqual(ctx['active_iteration_id'],4)
  self.assertEqual(ctx['source_mode'],'selected_files')

 def test_published_catalog_options_do_not_require_price_or_overwrite_source_brand(self):
  engine=SimpleNamespace(brand_index={})
  catalog=[{'brand':'ABB','category':'MCB','sku':'ACTUAL-CODE','source_url':'https://example.test/catalog.pdf',
            'specifications':{'Số cực':'1P','In (A)':'10','Icu (kA)':'6'}}]
  rows=suggest_takeoff_products([{'category':'MCB','name':'MCB','spec':'1P-10A-6kA','brand':'','quantity':1}],engine,catalog)
  self.assertEqual(rows[0]['catalog_candidates']['ABB'][0]['sku'],'ACTUAL-CODE')
  self.assertEqual(rows[0]['brand'],'')
  self.assertFalse(rows[0]['catalog_candidates']['ABB'][0]['auto_selectable'])
  wrong=suggest_takeoff_products([{'category':'MCB','name':'MCB','spec':'2P-10A-6kA','quantity':1}],engine,catalog)
  self.assertFalse(wrong[0]['catalog_candidates'])

if __name__=='__main__':unittest.main()

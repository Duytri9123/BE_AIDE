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
 def test_remote_tag_does_not_shrink_a_small_control_block_in_one_large_crop(self):
  parts=device_preview(Image.new('RGB',(1000,1000),'white'),{
      'symbol_box_2d':[709,666,715,680],'text_box_2d':[709,666,715,680],
      'tag_box_2d':[733,669,857,677]},tight=True)
  self.assertEqual([p['source_parts'] for p in parts],
      [['symbol_box_2d'],['tag_box_2d']])

 def test_rotated_native_label_trims_blank_borders_and_retains_text_marks(self):
  from PIL import ImageDraw
  from app.services.ai.evidence_preview import trim_native_text
  source=Image.new('RGB',(30,300),'white');draw=ImageDraw.Draw(source)
  draw.line((1,0,1,299),fill='black');draw.line((0,1,29,1),fill='black')
  draw.rectangle((8,240,20,280),fill='red');draw.rectangle((10,230,12,232),fill='blue')
  trimmed=trim_native_text(source)
  self.assertLess(trimmed.height,100)
  colors=set(trimmed.get_flattened_data())
  self.assertIn((255,0,0),colors);self.assertIn((0,0,255),colors)

 async def test_unclaimed_stale_tag_geometry_is_not_exported_as_a_device_part(self):
  from app.services.ai.device_crop_audit import audit_device_previews
  d=ExtractedDeviceSchema(name='Contactor',category='CONTACTOR',spec='')
  async def call(path,prompt):
   request=json.loads(prompt.rsplit('\n',1)[-1])[0]
   self.assertEqual([p['role'] for p in request['exported_parts']],['LABELED_BLOCK'])
   return json.dumps({'checks':[{'device_id':'0','matches':True,'symbol_complete':True,
       'label_complete':True,'identity_unambiguous':True}]})
  result=await audit_device_previews(Image.new('RGB',(1000,1000)),call,[d],{'boxes':[{
      'device_id':'0','symbol_box_2d':[100,100,120,200],'text_box_2d':[100,100,120,200],
      'tag_box_2d':[600,100,700,150],'source_annotation':'adjacent_control_functions'}]})
  self.assertTrue(result['boxes'][0]['verified']);self.assertIsNone(result['boxes'][0]['tag_box_2d'])

 def test_nearby_shared_header_stays_separate_from_the_target_source_symbol(self):
  source=Image.new('RGB',(1000,1000),'white')
  region={'symbol_box_2d':[100,300,140,330],'text_box_2d':[100,100,140,150],
      'shared_label':True,'relationship_evidence':'Shared heading group'}
  parts=device_preview(source,region,tight=True)
  devices=[p for p in parts if p['kind']=='device']
  self.assertEqual([p['source_parts'] for p in devices],[['symbol_box_2d'],['text_box_2d']])
  self.assertTrue(any(p['kind']=='relationship' for p in parts))

 async def test_isolated_audit_timeout_retries_only_failed_batch_once(self):
  from app.core.exceptions import AITimeoutError
  from app.services.ai.device_crop_audit import audit_device_previews
  devices=[ExtractedDeviceSchema(name='MCB',category='MCB',spec='') for _ in range(2)]
  boxes=[{'device_id':str(i),'symbol_box_2d':[100+i*200,100,200+i*200,200],
      'text_box_2d':[80+i*200,100,100+i*200,200]} for i in range(2)]
  seen=[]
  async def call(path,prompt):
   identity=json.loads(prompt.rsplit('\n',1)[-1])[0]['device_id'];seen.append(identity)
   if identity=='0' and seen.count('0')==1:raise AITimeoutError('network timeout')
   return json.dumps({'checks':[{'device_id':identity,'matches':True,
      'symbol_complete':True,'label_complete':True,'identity_unambiguous':True}]})
  result=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,
      devices,{'boxes':boxes},batch_size=1,concurrency=2)
  self.assertEqual(seen.count('0'),2);self.assertEqual(seen.count('1'),1)
  self.assertFalse(result['processing_interrupted'])
  self.assertTrue(all(b['verified'] for b in result['boxes']))

 def test_source_template_repairs_geometry_without_copying_reference_device_ratings(self):
  from PIL import ImageDraw
  from app.services.ai.source_crop_repair import local_source_repairs
  source=Image.new('RGB',(1000,1000),'white');draw=ImageDraw.Draw(source)
  for cy in (200,400):
   draw.line((180,cy,200,cy),fill='black',width=2)
   draw.ellipse((198,cy-3,204,cy+3),outline='black',width=2)
   draw.line((204,cy,222,cy-12),fill='black',width=2)
   draw.ellipse((220,cy-3,226,cy+3),outline='black',width=2)
   draw.line((226,cy,246,cy),fill='black',width=2)
  devices=[ExtractedDeviceSchema(name='MCB',category='MCB',spec=spec,quantity=1,
      source_observations={'coverage_review':{'region':{'wire_band':True}}})
      for spec in ('1P 10A 6kA','1P 16A 6kA')]
  audited={'boxes':[{'device_id':'0','verified':True,'symbol_box_2d':[185,178,205,248]},
      {'device_id':'1','verified':False,'symbol_box_2d':[396,210,403,225],
       'text_box_2d':[370,180,389,260]}]}
  proposals=local_source_repairs(source,devices,audited)
  self.assertEqual(len(proposals),1)
  self.assertEqual(proposals[0]['device_id'],'1')
  box=proposals[0]['symbol_box_2d']
  self.assertLess(box[0],390);self.assertGreater(box[2],403)
  self.assertLess(box[1],198);self.assertGreater(box[3],226)
  self.assertEqual(devices[1].spec,'1P 16A 6kA')
  self.assertNotIn('audit_observed',proposals[0])
  self.assertEqual(local_source_repairs(Image.new('RGB',(1000,1000),'white'),devices,audited),[])

 def test_compact_breaker_label_and_full_quantity_annotation_remain_separate_fields(self):
  from app.services.ai.scoped_takeoff import normalize_scoped_row
  row=normalize_scoped_row({'category':'CIRCUIT_BREAKER','name':'Aptomat tép','quantity':1,
      'observed_text':'MCB1P 16A-10kA','spec':'16A-10kA'})
  self.assertEqual(row['category'],'MCB')
  note='MỖI LỘ 1 NÚT ẤN ĐIỀU KHIỂN (9 NÚT ẤN)'
  row=normalize_scoped_row({'category':'CONTROL_COMPONENT','name':'Nút ấn điều khiển',
      'quantity':9,'spec':note,'observed_text':note})
  self.assertEqual((row['category'],row['spec'],row['quantity_basis']),('BUTTON','',note))

 def test_dol_label_does_not_inherit_the_upstream_breaker_rating(self):
  from app.services.ai.scoped_takeoff import normalize_scoped_row
  row=normalize_scoped_row({'category':'CONTACTOR','name':'DOL','observed_text':'DOL',
      'spec':'DOL 3P 25A 6kA','in_a':'25A','poles':'3P','icu_ka':'6kA','quantity':1})
  self.assertEqual((row['category'],row['spec'],row['unit']),('DOL','DOL','Bộ'))
  self.assertTrue(all(row[k] is None for k in ('in_a','poles','icu_ka')))
  self.assertEqual(len(row['source_observations']['unverified_claims']),3)

 def test_material_note_distinguishes_total_quantity_from_per_branch_factor(self):
  from app.services.ai.material_note_evidence import material_annotation
  row={'name':'Nút ấn điều khiển','category':'BUTTON','quantity':9,
       'observed_text':'MỖI LỘ 1 NÚT ẤN ĐIỀU KHIỂN (9 NÚT ẤN)'}
  self.assertEqual(material_annotation(row)['quantity'],9)
  self.assertIsNone(material_annotation({**row,'quantity':1}))

 async def test_material_note_requires_independent_text_and_quantity_checks_without_claiming_a_symbol(self):
  from app.services.ai.device_crop_audit import audit_device_previews
  from app.services.ai.material_note_evidence import material_annotation
  note=material_annotation({'category':'BUTTON','name':'Nút ấn','quantity':9,'observed_text':'9 NÚT ẤN'})
  d=ExtractedDeviceSchema(name='Nút ấn',category='BUTTON',quantity=9,spec='',
      source_observations={'material_annotation':note})
  box={'device_id':'0','text_box_2d':[100,100,130,300]}
  for quantity_ok in (False,True):
   call=AsyncMock(return_value=json.dumps({'checks':[{'device_id':'0','matches':False,
      'symbol_complete':False,'label_complete':True,'note_complete':True,'note_matches':True,
      'quantity_matches':quantity_ok,'observed':'9 NÚT ẤN'}]}))
   result=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,[d],{'boxes':[box]})
   self.assertEqual(result['boxes'][0]['verified'],quantity_ok)
   apply_verified_boxes([d],result,require_symbols=True)
   self.assertEqual(d.evidence_region['status']=='verified',quantity_ok)
   if quantity_ok:
    self.assertFalse(result['boxes'][0]['symbol_verified'])
    self.assertEqual(d.evidence_region['evidence_kind'],'material_note')
    self.assertIn('Ghi chú',device_preview(Image.new('RGB',(1000,1000)),d.evidence_region,tight=True)[0]['label'])

 def test_measurement_and_indicator_functions_are_not_source_ratings(self):
  from app.services.ai.scoped_takeoff import normalize_scoped_row
  for category,spec in [('METER','Đo dòng điện'),('METER','Đo điện áp'),
      ('LIGHT','Đèn báo trạng thái pha'),('SELECTOR_SWITCH','Chuyển mạch đo vôn')]:
   row=normalize_scoped_row({'name':category,'category':category,'spec':spec,'quantity':1})
   self.assertEqual(row['spec'],'')
   self.assertEqual(row['electrical_function'],spec)
   self.assertEqual(row['source_observations']['function_in_spec'],spec)
  self.assertEqual(normalize_scoped_row({'category':'METER','spec':'0-500V','quantity':1})['spec'],'0-500V')

 async def test_audit_provider_failure_preserves_other_batches_without_recovery(self):
  from app.core.exceptions import AITimeoutError
  from app.services.ai.device_crop_audit import audit_device_previews
  devices=[ExtractedDeviceSchema(name='MCB',category='MCB',spec='') for _ in range(2)]
  boxes=[{'device_id':str(i),'symbol_box_2d':[100,100,200,200],
      'text_box_2d':[80,100,100,200]} for i in range(2)]
  async def call(path,prompt):
   identity=json.loads(prompt.rsplit('\n',1)[-1])[0]['device_id']
   if identity=='0':raise AITimeoutError('provider timed out')
   return json.dumps({'checks':[{'device_id':identity,'matches':True,
       'symbol_complete':True,'label_complete':True,'identity_unambiguous':True,
       'shared_label_matches':True}]})
  # Use distinct labels so this is not interpreted as a shared-header claim.
  boxes[1]['text_box_2d']=[280,100,300,200]
  audited=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,
      devices,{'boxes':boxes},batch_size=1,concurrency=2)
  self.assertTrue(audited['processing_interrupted'])
  by_id={b['device_id']:b for b in audited['boxes']}
  self.assertFalse(by_id['0']['verified'])
  self.assertIn('Máy chủ AI',by_id['0']['audit_reason'])
  self.assertTrue(by_id['1']['verified'])
  no_more_calls=AsyncMock(side_effect=AssertionError('must not retry outage'))
  self.assertIs(await complete_evidence(Image.new('RGB',(1000,1000)),
      'unused.png',devices,audited,no_more_calls),audited)
  no_more_calls.assert_not_awaited()

 async def test_recovery_provider_failure_keeps_existing_checks_and_stops(self):
  from app.core.exceptions import AIVisionError
  devices=[ExtractedDeviceSchema(name='MCB',category='MCB',spec='') for _ in range(2)]
  good={'device_id':'0','verified':True,'symbol_box_2d':[100,100,200,200]}
  provider=AsyncMock(side_effect=AIVisionError('provider disconnected'))
  result=await complete_evidence(Image.new('RGB',(1000,1000)), 'unused.png',
      devices,{'boxes':[good]},provider)
  self.assertTrue(result['processing_interrupted'])
  self.assertEqual(provider.await_count,1)
  by_id={b['device_id']:b for b in result['boxes']}
  self.assertEqual(by_id['0'],good)
  self.assertTrue(by_id['1']['processing_interrupted'])
  self.assertTrue(evidence_gaps(devices[1],by_id['1']))

 async def test_many_repairs_use_bounded_groups_and_preserve_global_ids(self):
  devices=[ExtractedDeviceSchema(name='MCB '+str(i),category='MCB',spec='',source_observations={
      'coverage_review':{'region':{'box_2d':[200,0,400,1000]}}}) for i in range(9)]
  requests=[]
  async def call(path,prompt):
   rows=json.loads(prompt.rsplit('Các dòng cần đọc lại: ',1)[-1]);requests.append(rows)
   with Image.open(path) as source:self.assertEqual(source.size,(1000,300))
   return json.dumps({'boxes':[{'device_id':r['device_id'],'verified':True,'symbol_verified':True,
        'symbol_box_2d':[100,100,200,200],'text_box_2d':[100,100,200,200]} for r in rows]})
  async def audit(image,provider,devices,payload,**kwargs):return payload
  with patch('app.services.ai.device_crop_audit.audit_device_previews',new=audit):
   result=await complete_evidence(Image.new('RGB',(1000,1000)),'unused.png',devices,{'boxes':[]},call,concurrency=3)
  self.assertEqual(sorted(len(r) for r in requests),[1,4,4])
  self.assertEqual({r['device_id'] for r in result['boxes']},{str(i) for i in range(9)})
  self.assertTrue(all(r['symbol_box_2d']==[180,100,210,200] for r in result['boxes']))

 async def test_missing_provider_flags_still_receive_independent_pixel_check(self):
  from app.services.ai.device_crop_audit import audit_device_previews
  d=ExtractedDeviceSchema(category='MCB',name='MCB',spec='3P 63A 10kA')
  box={'device_id':'0','symbol_box_2d':[100,100,200,200], 'text_box_2d':[80,100,100,200]}
  call=AsyncMock(return_value=json.dumps({'checks':[{'device_id':'0','matches':True,
      'symbol_complete':True,'label_complete':True,'identity_unambiguous':True}]}))
  result=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,[d],{'boxes':[box]})
  self.assertEqual(call.await_count,1)
  self.assertTrue(result['boxes'][0]['verified'])
  rejected=await audit_device_previews(Image.new('RGB',(1000,1000),'white'),call,[d],
      {'boxes':[{**box,'symbol_verified':False}]})
  self.assertEqual(call.await_count,1)
  self.assertFalse(rejected['boxes'][0]['verified'])

 def test_generic_source_categories_do_not_hide_explicit_device_identity(self):
  from app.services.ai.scoped_takeoff import normalize_scoped_row
  for category,name,spec,expected in [('PROTECTIVE','Aptomat tép','MCB-3P-63A-10kA','MCB'),
      ('MEASURING','Biến dòng đo lường','80/5A','CT'),
      ('MEASURING','Đồng hồ đo dòng điện','A','METER'),
      ('PROTECTIVE','Cầu chì hạ thế','2A','FUSE')]:
   row=normalize_scoped_row(dict(category=category,name=name,spec=spec))
   self.assertEqual(row['category'],expected)

 def test_phase_labels_do_not_establish_lamp_operating_voltage(self):
  from app.services.ai.scoped_takeoff import ground_scoped_identity
  row=ground_scoped_identity({'category':'LIGHT','name':'Đèn báo pha','spec':'220V','quantity':3},
      [{'text':'R, Y, B'}])
  self.assertEqual(row['spec'],'')
  self.assertEqual(row['source_observations']['unverified_claims'][0]['value'],'220V')
  confirmed=ground_scoped_identity({'category':'LIGHT','name':'Đèn báo pha','spec':'24V'},
      [{'text':'24V'}])
  self.assertEqual(confirmed['spec'],'24V')

 def test_native_row_identity_merges_overlap_but_keeps_repeated_spare_tags(self):
  from app.services.ai.cad_branch_evidence import bind_horizontal_rows
  evidence={'view_bounds':[0,0,1000,1000], 'labels':[
      {'id':'tag1','text':'DP','bounds':[400,600,420,620],'y':600,'height':20},
      {'id':'rating1','text':'MCB-1P-32A-6kA','bounds':[190,600,310,620],'y':600,'height':20},
      {'id':'tag2','text':'DP','bounds':[400,500,420,520],'y':500,'height':20},
      {'id':'rating2','text':'MCB-1P-32A-6kA','bounds':[190,500,310,520],'y':500,'height':20}],
      'rows':[{'id':'tag1','rating_id':'rating1','tag':'DP','rating':'MCB-1P-32A-6kA'},
              {'id':'tag2','rating_id':'rating2','tag':'DP','rating':'MCB-1P-32A-6kA'}]}
  row={'category':'MCB','tag':'DP','spec':'1P-32A-6kA','quantity':1}
  boxes=[{'device_id':'0','text_box_2d':[380,190,400,310]},
         {'device_id':'1','text_box_2d':[381,192,399,309]},
         {'device_id':'2','text_box_2d':[480,190,500,310]}]
  rows,proposals=bind_horizontal_rows(evidence,[dict(row) for _ in range(3)],boxes)
  self.assertEqual(len(rows),2)
  self.assertEqual([r['source_evidence_ids'][-1] for r in rows],['rating1','rating2'])
  self.assertEqual([p['device_id'] for p in proposals],['0','1'])

 def test_horizontal_row_load_uses_complete_native_label_outside_discovery_crop(self):
  from app.services.ai.cad_branch_evidence import seed_horizontal_row_boxes
  evidence={'view_bounds':[0,0,1000,1000], 'labels':[
      {'id':'tag','text':'S1','bounds':[400,600,420,620],'y':600,'height':20},
      {'id':'rating','text':'RCBO-1P+N-25A-30mA-6kA','bounds':[190,600,310,620],'y':600,'height':20},
      {'id':'load','text':'Ổ CẮM','bounds':[850,600,950,620],'y':600,'height':20}],
      'rows':[{'id':'tag','rating_id':'rating','tag':'S1','rating':'RCBO-1P+N-25A-30mA-6kA'}]}
  proposal={'device_id':'0','symbol_box_2d':[400,200,430,230],'load_box_2d':[400,846,410,847]}
  result=seed_horizontal_row_boxes(evidence,[{'tag':'S1','spec':'RCBO-1P+N-25A-30mA-6kA','connected_load':'Ổ CẮM'}],[proposal])[0]
  self.assertEqual(result['load_box_2d'],[380,850,400,950])
  self.assertEqual(result['symbol_box_2d'],proposal['symbol_box_2d'])
  self.assertNotIn('audit_observed',result)  # Native anchors still require independent pixel checking.

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

 def test_phase_count_and_neutral_pole_designation_are_not_interchangeable(self):
  catalog=[{'brand':'ABB','category':'RCBO','sku':'NEUTRAL','source_url':'https://example.test/rcbo',
            'specifications':{'Số cực':'1P+N','In (A)':'25','Icu (kA)':'6'}},
           {'brand':'ABB','category':'RCBO','sku':'TWO','source_url':'https://example.test/rcbo',
            'specifications':{'Số cực':'2P','In (A)':'25','Icu (kA)':'6'}}]
  result=suggest_takeoff_products([{'name':'RCBO','category':'RCBO','spec':'1P+N-25A-6kA','poles':2}],catalog_rows=catalog)[0]
  self.assertEqual([x['sku'] for x in result['catalog_candidates']['ABB']],['NEUTRAL'])
  unknown=suggest_takeoff_products([{'name':'MCB ba pha','category':'MCB','spec':'25A 6kA'}],catalog_rows=[])[0]
  self.assertEqual(unknown['selection_analysis']['status'],'insufficient_source_specs')

 def test_fuse_proposals_match_source_current(self):
  catalog=[{'brand':'ABB','category':'FUSE','sku':str(current),'source_url':'https://example.test/fuse',
            'specifications':{'In (A)':str(current)}} for current in (2,10)]
  result=suggest_takeoff_products([{'name':'Cầu chì hạ thế','category':'PROTECTIVE','spec':'2A'}],catalog_rows=catalog)[0]
  self.assertEqual([x['sku'] for x in result['catalog_candidates']['ABB']],['2'])

 def test_residual_current_must_match_including_catalog_name_labels(self):
  catalog=[{'brand':'Mitsubishi','category':'RCBO','sku':str(residual),
            'item_name':f'RCBO 1PN 25A {residual}MA','source_url':'https://example.test/rcbo',
            'specifications':{'In (A)':'25','Số cực':'1P+N','Icu (kA)':'6'}} for residual in (30,100,300)]
  result=suggest_takeoff_products([{'name':'RCBO','category':'RCBO','spec':'1P+N-25A-30mA-6kA','poles':2}],catalog_rows=catalog)[0]
  self.assertEqual([x['sku'] for group in result['catalog_candidates'].values() for x in group],['30'])

 def test_pole_count_and_meter_marking_are_not_source_phase_or_ratings(self):
  from app.services.ai.scoped_takeoff import normalize_scoped_row
  row=normalize_scoped_row({'name':'Ampe kế','category':'METER','spec':'Chỉ thị kim/số (a)',
      'source_observations':{'circuit':{'phase':'3P'}}})
  self.assertEqual(row['spec'],'')
  self.assertIsNone(row['source_observations']['circuit']['phase'])
  self.assertEqual(row['source_observations']['symbol_marking'],'Chỉ thị kim/số (a)')

if __name__=='__main__':unittest.main()

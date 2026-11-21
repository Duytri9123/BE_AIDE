import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from PIL import Image
from app.services.ai.regional_takeoff import extract_regions, map_box, deduplicate_parts
from app.services.ai.motor_starter_context import enrich_motor_starters


async def keep_disputes(image, regions, parts, issues, call_image, **kwargs):
    return issues, []


class RegionalTests(unittest.IsolatedAsyncioTestCase):
    def test_cad_branch_tag_in_load_does_not_duplicate_the_native_breaker(self):
        from app.services.ai.cad_branch_evidence import merge_vertical_candidates
        image_row = {'category': 'MCB', 'connected_load': 'L1. Chiếu sáng'}
        native_row = {'tag': 'L1', 'category': 'MCB', 'connected_load': 'CHIẾU SÁNG',
                      'spec': '1P 16A 6kA', 'source_observations': {}}
        part = {'devices': [image_row], 'boxes': []}
        merge_vertical_candidates([part], [{'box_2d': [0, 0, 1000, 1000]}], {
            'devices': [native_row], 'boxes': [{'load_box_2d': [200, 500, 300, 900]}],
        })
        self.assertEqual(part['devices'], [native_row])

    async def test_whole_panel_uses_the_same_frame_for_read_and_review(self):
        call = AsyncMock(side_effect=[json.dumps({'devices': [['MCB', 'MCB', 'Q1', '2P 20A', 1, 'Cái',
                                                             None, 'MCB 2P 20A']]}),
                                     json.dumps({'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'panel.png'
            Image.new('RGB', (1200, 900)).save(path)
            result = await extract_regions(path, 'Bóc tách tủ', call, whole_panel=True)
            self.assertEqual([Path(event.args[0]) for event in call.await_args_list], [path, path])
        review = result['devices'][0]['source_observations']['coverage_review']
        self.assertEqual((review['status'], review['method']), ('passed', 'whole_panel'))
        self.assertEqual((result['devices'][0]['tag'], result['devices'][0]['poles']), ('Q1', 2))

    async def test_overlap_needs_checked_source_geometry_before_removing_a_repeated_spare(self):
        import copy
        from app.services.ai.regional_takeoff import check_overlap_geometry
        row={'name':'MCB','category':'MCB','quantity':1,'spec':'1P 16A 10kA',
             'in_a':16,'poles':1,'icu_ka':10,'observed_text':'MCB-1P 16A-10kA'}
        source=[{'devices':[dict(row),dict(row)],'boxes':[
            {'device_id':'0','symbol_box_2d':[802,129,822,166]},
            {'device_id':'1','symbol_box_2d':[851,126,872,166]}]},
            {'devices':[dict(row)],'boxes':[{'device_id':'0','symbol_box_2d':[841,114,857,158]}]}]
        issues=[{'region_id':'1','device_indices':[0],'field':'quantity','reason':'Trùng/thừa một MCB dự phòng'}]
        regions=[{'box_2d':[655,0,895,1000]},{'box_2d':[805,0,1000,1000]}]
        async def keep(image,path,devices,audited,*args,**kwargs):return audited
        for verified in (False,True):
            parts=copy.deepcopy(source)
            checked={'boxes':[{'device_id':str(i),'verified':verified,'symbol_verified':verified,
                'symbol_box_2d':[851,126,872,166],'text_box_2d':[830,120,850,175]} for i in range(2)]}
            audit=AsyncMock(return_value=checked)
            with patch('app.services.ai.device_crop_audit.audit_device_previews',audit), \
                 patch('app.services.ai.takeoff_evidence_completion.complete_evidence',keep):
                await check_overlap_geometry(Image.new('RGB',(1000,1000)),'source.png',regions,parts,issues,AsyncMock())
            self.assertEqual(len(audit.await_args.args[2]),2)
            deduplicate_parts(parts)
            self.assertEqual([len(p['devices']) for p in parts],[2,0] if verified else [2,1])
            self.assertEqual(parts[0]['boxes'][0]['symbol_box_2d'],[802,129,822,166])

    async def test_explicit_locator_load_is_canonicalized_without_marking_it_verified(self):
        call=AsyncMock(side_effect=[json.dumps({'regions':[]}),
            json.dumps({'devices':[{'name':'MCB','category':'MCB','quantity':1}],
                'boxes':[{'device_id':'0','load_box_2d':[200,800,220,950],
                    'load_label':'VAN ĐIỆN TỪ 02','relationship_evidence':'Dây của nhánh này đến van 02'}]}),
            json.dumps({'issues':[]})])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(result['devices'][0]['connected_load'],'VAN ĐIỆN TỪ 02')
        self.assertNotIn('load_verified',result['boxes'][0])

    async def test_isolated_coverage_timeout_retries_once_after_completed_reads(self):
        from app.core.exceptions import AIVisionError
        call=AsyncMock(side_effect=[json.dumps({'regions':[]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),
            AIVisionError('Hết thời gian chờ',{'last_error_type':'AITimeoutError'}),
            json.dumps({'issues':[]})])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(call.await_count,4)
        self.assertFalse(result['processing_interrupted'])
        self.assertEqual(result['devices'][0]['source_observations']['coverage_review']['status'],'passed')

    def test_common_branch_tag_is_only_proposed_from_an_unambiguous_printed_anchor(self):
        from app.services.ai.table_image_context import propose_branch_tags
        parts=[{'devices':[{'tag':'P4','connected_load':'Bơm 04'},
                           {'category':'POWER_SUPPLY','connected_load':'Bơm 04'},
                           {'tag':'P5','connected_load':'Bơm chung'},
                           {'tag':'P6','connected_load':'Bơm chung'},
                           {'category':'CONTACTOR','connected_load':'Bơm chung'}],
                'boxes':[{'device_id':str(i),'tag_box_2d':[i,1,i+1,2]} for i in range(5)]}]
        propose_branch_tags(parts)
        self.assertEqual(parts[0]['devices'][1]['tag'],'P4')
        self.assertEqual(parts[0]['boxes'][1]['tag_box_2d'],[0,1,1,2])
        self.assertNotIn('tag',parts[0]['devices'][4])
        self.assertNotIn('verified',parts[0]['boxes'][1])

    async def test_malformed_coverage_retries_once_with_the_same_schema(self):
        calls=[]
        async def call(path,prompt,**kwargs):
            calls.append(kwargs)
            if len(calls)==1:return json.dumps({'regions':[{'box_2d':[0,0,1000,1000]}]})
            if len(calls)==2:return json.dumps({'devices':[],'boxes':[]})
            if len(calls)==3:return '{"issues":[{"device_indices": [0], 1, 2]}'
            return '{"issues":[]}'
        call.supports_json_schema=True
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(100,100)).save(path)
            result=await extract_regions(path,'Read',call)
        from app.services.ai.regional_takeoff import COVERAGE_SCHEMA, REGION_SCHEMA
        self.assertEqual(len(calls),4)
        self.assertEqual(calls[1],{'response_schema':REGION_SCHEMA})
        self.assertTrue({'tag_box_2d','load_box_2d','relationship_evidence'}.issubset(
            REGION_SCHEMA['properties']['boxes']['items']['required']))
        self.assertEqual(calls[2],{'response_schema':COVERAGE_SCHEMA})
        self.assertEqual(calls[2],calls[3])

    def test_row_bands_use_each_wire_angle_when_a_photo_has_no_single_global_slope(self):
        from PIL import ImageDraw
        from app.services.ai.table_image_context import row_slope,circuit_bands,owns_symbol
        source=Image.new('RGB',(1000,1000),'white');draw=ImageDraw.Draw(source)
        for i,y in enumerate(range(100,800,100)):
            slope=.1-i/30
            draw.line((50,round(y+slope*(50-250)),950,round(y+slope*(950-250))),fill='black',width=2)
        self.assertIsNone(row_slope(source))
        bands=circuit_bands(source,None)
        self.assertGreaterEqual(len(bands),3)
        for i,y in enumerate(range(100,800,100)):
            slope=.1-i/30;cy=y+slope*(800-250)
            self.assertEqual(sum(owns_symbol([cy-2,798,cy+2,802],b['ownership_y'],None) for b in bands),1)

    def test_photographed_row_ownership_projects_load_side_symbols_along_source_wires(self):
        from PIL import ImageDraw
        from app.services.ai.table_image_context import row_slope,owns_symbol
        source=Image.new('RGB',(1000,1000),'white');draw=ImageDraw.Draw(source)
        for y in range(100,800,100):draw.line((50,y,950,y+54),fill='black',width=2)
        slope=row_slope(source)
        self.assertIsNotNone(slope);self.assertAlmostEqual(slope,.06,delta=.01)
        breaker=[195,195,205,205];supply=[231,795,241,805]
        for box in (breaker,supply):
            self.assertTrue(owns_symbol(box,[150,230],slope))
            self.assertFalse(owns_symbol(box,[230,310],slope))

    def test_shared_voltage_reference_only_applies_to_the_bound_source_column(self):
        from app.services.ai.table_image_context import shared_source_references
        parts=[{'devices':[{'name':'Bộ nguồn','category':'POWER_SUPPLY','spec':''},
                           {'name':'Bộ nguồn','category':'POWER_SUPPLY','spec':''}],
                'boxes':[{'device_id':'0','symbol_box_2d':[200,800,230,830]},
                         {'device_id':'1','symbol_box_2d':[200,300,230,330]}]}]
        ref={'category':'POWER_SUPPLY','text':'BỘ ĐỔI NGUỒN CHO BƠM 220/24V','spec':'220/24V',
             'box_2d':[100,780,120,930],'applies_to_box_2d':[150,790,450,840]}
        shared_source_references(parts,[{**ref,'spec':'220/48V'}])
        self.assertEqual(parts[0]['devices'][0]['spec'],'')
        shared_source_references(parts,[ref])
        self.assertEqual(parts[0]['devices'][0]['spec'],'220/24V')
        self.assertEqual(parts[0]['devices'][1]['spec'],'')
        self.assertEqual(parts[0]['boxes'][0]['text_box_2d'],ref['box_2d'])
        self.assertNotIn('audit_observed',parts[0]['boxes'][0])

    def test_overlap_containment_joins_partial_rating_but_keeps_conflicting_current(self):
        partial={'name':'MCB','category':'MCB','tag':'P1','quantity':1,
                 'spec':'16A-10kA','in_a':16,'poles':1}
        complete={**partial,'spec':'MCB-1P-16A-10kA','connected_load':'Bơm 01'}
        parts=[{'devices':[partial],'boxes':[{'device_id':'0','symbol_box_2d':[100,100,120,160]}]},
               {'devices':[complete,{**complete,'spec':'1P20A10kA','in_a':20}],
                'boxes':[{'device_id':str(i),'symbol_box_2d':[103,110,117,150]} for i in range(2)]}]
        deduplicate_parts(parts)
        self.assertEqual([len(p['devices']) for p in parts],[1,1])
        self.assertEqual(parts[0]['devices'][0]['connected_load'],'Bơm 01')
        self.assertEqual(parts[1]['devices'][0]['in_a'],20)

    async def test_provider_outage_keeps_read_regions_and_skips_further_ai_calls(self):
        from app.core.exceptions import AIVisionError
        call=AsyncMock(side_effect=[json.dumps({'regions':[
            {'box_2d':[0,0,500,1000]}, {'box_2d':[500,0,1000,1000]}]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),AIVisionError('provider unavailable')])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call,concurrency=2)
        self.assertEqual(call.await_count,3)
        self.assertTrue(result['processing_interrupted'])
        self.assertEqual(len(result['devices']),1)
        review=result['devices'][0]['source_observations']['coverage_review']
        self.assertEqual(review['status'],'needs_review')
        self.assertTrue(review['read_failed'])
        self.assertIn('Máy chủ AI',review['issues'][0]['reason'])

    async def test_isolated_region_timeout_retries_only_the_failed_read_once(self):
        from app.core.exceptions import AIVisionError
        call=AsyncMock(side_effect=[json.dumps({'regions':[
            {'box_2d':[0,0,500,1000]},{'box_2d':[500,0,1000,1000]}]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),AIVisionError('Máy chủ gián đoạn',
                {'last_error':'Hết thời gian chờ 60s','last_error_type':'AITimeoutError','retryable_transport':True}),
            json.dumps({'devices':[{'name':'TIMER','quantity':1}]}),json.dumps({'issues':[]})])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call,concurrency=2)
        self.assertEqual(call.await_count,5)
        self.assertEqual([r['name'] for r in result['devices']],['MCB','TIMER'])
        self.assertFalse(result['processing_interrupted'])

    async def test_partial_timeout_recovers_three_failed_regions_without_rereading_success(self):
        from app.core.exceptions import AITimeoutError

        layout = {'regions': [{'box_2d': [250*i, 0, 250*(i+1), 1000]} for i in range(4)]}
        first = {'devices': [{'name': 'MCB', 'quantity': 1}]}
        call = AsyncMock(side_effect=[json.dumps(layout), json.dumps(first),
                                     *(AITimeoutError('timeout') for _ in range(3)),
                                     *[json.dumps({'devices': []})]*3, json.dumps({'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.png'
            Image.new('RGB', (1000, 1000)).save(path)
            result = await extract_regions(path, 'Read', call, concurrency=2)
        self.assertEqual(call.await_count, 9)
        self.assertEqual([r['name'] for r in result['devices']], ['MCB'])
        self.assertFalse(result['processing_interrupted'])

    async def test_provider_outage_during_review_preserves_inventory_without_retry(self):
        from app.core.exceptions import AIVisionError
        call=AsyncMock(side_effect=[json.dumps({'regions':[]}),
            json.dumps({'devices':[{'name':'MCB','quantity':1}]}),AIVisionError('provider disconnected')])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(call.await_count,3)
        self.assertTrue(result['processing_interrupted'])
        self.assertEqual(result['devices'][0]['source_observations']['coverage_review']['status'],'needs_review')

    def test_overlap_read_without_tag_is_merged_only_at_same_source_geometry(self):
        parts=[{'devices':[{'name':'Contactor','category':'CONTACTOR','spec':'2P16A','tag':'P1','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':[100,100,150,140]}]},
               {'devices':[{'name':'Khởi động từ','category':'Điều khiển','spec':'2P16A','tag':None,'quantity':1},
                           {'name':'Contactor','category':'CONTACTOR','spec':'2P16A','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':[101,100,151,140]},
                         {'device_id':'1','symbol_box_2d':[200,100,250,140]}]}]
        deduplicate_parts(parts)
        self.assertEqual(sum(len(p['devices']) for p in parts),2)
        self.assertEqual(parts[1]['boxes'][0]['symbol_box_2d'],[200,100,250,140])

    def test_coverage_retains_source_claims_without_repeated_images_or_diagnostics(self):
        from app.services.ai.regional_takeoff import coverage_claim
        row={'name':'MCB','tag':'P1','spec':'16A','quantity':1,'connected_load':'Bơm',
             'evidence_image':'data:image/png;base64,large','technical_analysis':'repeated explanation',
             'source_observations':{'panel_notes':['repeated note']*100,'circuit':{'power_w':100},
                 'source_checks':[{'field':'quantity','value':1,'observed_text':'1 cái',
                     'verification_status':'verified','evidence_image':'large','reason':'diagnostic'}]}}
        result=coverage_claim(row)
        for key in ('name','tag','spec','quantity','connected_load'):self.assertEqual(result[key],row[key])
        self.assertEqual(result['source_observations']['source_checks'][0]['observed_text'],'1 cái')
        self.assertNotIn('base64',json.dumps(result))
        self.assertNotIn('panel_notes',json.dumps(result))
        self.assertNotIn('technical_analysis',result)

    def test_omitted_device_repair_uses_the_source_region_that_contains_it(self):
        from app.services.ai.regional_takeoff import review_issue_region
        regions = [{'box_2d': [0, 0, 289, 1000]}, {'box_2d': [199, 0, 507, 1000]}]
        issue = {'region_id': '0', 'field': 'devices', 'device_indices': [], 'box_2d': [303, 50, 336, 98]}
        self.assertEqual(review_issue_region(issue, regions), 1)
        self.assertEqual(review_issue_region({**issue, 'device_indices': [0]}, regions), 0)

    def test_spare_overlap_with_same_rating_and_load_labels_counts_once(self):
        row = {'category': 'MCB', 'spec': '16A-10kA', 'quantity': 1}
        parts = [
            {'devices': [{**row, 'observed_text': 'MCB-1P 16A-10kA DỰ PHÒNG'}],
             'boxes': [{'device_id': '0', 'symbol_box_2d': [855, 134, 874, 163],
                        'text_box_2d': [824, 118, 854, 180], 'load_box_2d': [838, 804, 857, 885]}]},
            {'devices': [{**row, 'observed_text': 'MCB-1P 16A-10kA'}, row.copy()],
             'boxes': [{'device_id': '0', 'symbol_box_2d': [842, 131, 872, 161],
                        'text_box_2d': [824, 117, 857, 180], 'load_box_2d': [838, 804, 856, 886]},
                       {'device_id': '1', 'symbol_box_2d': [795, 135, 813, 163],
                        'text_box_2d': [765, 119, 794, 181], 'load_box_2d': [783, 804, 800, 885]}]}
        ]
        deduplicate_parts(parts)
        self.assertEqual([len(part['devices']) for part in parts], [1, 1])
        self.assertEqual(parts[1]['boxes'][0]['symbol_box_2d'], [795, 135, 813, 163])

    async def test_overlapping_table_bands_read_full_symbol_but_count_it_once(self):
        import numpy as np
        scan={'layout_kind':'horizontal_circuit_table','regions':[
            {'box_2d':[0,0,500,500]},{'box_2d':[500,0,1000,500]},
            {'box_2d':[0,500,500,1000]}]}
        reads=[]
        async def call(path,prompt):
            if 'Nhận diện vùng trước' in prompt:return json.dumps(scan)
            if 'Kiểm kê ĐỘC LẬP' in prompt:
                request = json.loads(prompt.rsplit('\n', 1)[-1])
                rows = [dict(zip(request['device_columns'], values))
                        for region in request['regions'] for values in region['devices']]
                self.assertEqual([(row['tag'], row['spec'], row['quantity']) for row in rows],
                                 [('P1', '16A', 1)])
                return json.dumps({'issues': []})
            with Image.open(path) as crop:
                ink=np.asarray(crop)[:,:,0]<100
                ys,xs=np.where(ink)
                if not len(xs):return json.dumps({'devices':[]})
                reads.append((int(ys.max()-ys.min()+1),crop.height))
                box=[int(ys.min()/crop.height*1000),int(xs.min()/crop.width*1000),
                     round((ys.max()+1)/crop.height*1000),round((xs.max()+1)/crop.width*1000)]
            return json.dumps({'devices':[{'name':'MCB','tag':'P1','category':'MCB','spec':'16A','quantity':1}],
                'boxes':[{'device_id':'0','symbol_box_2d':box,'text_box_2d':box}]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';image=Image.new('RGB',(1000,1000),'white')
            image.paste('black',(200,225,220,235));image.save(path)
            result=await extract_regions(path,'Read',call,concurrency=6)
        self.assertGreaterEqual(len(reads),2)
        self.assertTrue(all(height==10 for height,_ in reads))
        self.assertEqual(len(result['devices']),1)
        self.assertEqual(result['devices'][0]['tag'],'P1')

    async def test_dense_table_columns_become_bounded_horizontal_bands(self):
        scan={'layout_kind':'horizontal_circuit_table','regions':[
            {'box_2d':box} for box in ([50,40,350,400],[360,200,650,430],[650,220,950,430],[100,520,370,998])],
            'inventory':[{'quantity':37}]}
        sizes=[]
        async def call(path,prompt):
            with Image.open(path) as source:sizes.append(source.size)
            return json.dumps(scan if len(sizes)==1 else {'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call,concurrency=6)
        self.assertEqual(len(sizes),8)  # Scan, six bounded bands, independent coverage.
        self.assertTrue(all(w==1000 and h<=270 for w,h in sizes[1:-1]))
        self.assertGreaterEqual(sum(h for _,h in sizes[1:-1]),1000)

    async def test_rotated_table_keeps_source_rows_along_the_rotated_axis(self):
        sizes=[]
        async def call(path,prompt):
            with Image.open(path) as source:sizes.append(source.size)
            return json.dumps({'layout_kind':'horizontal_circuit_table','regions':[
                {'box_2d':[100,200,500,300],'rotation_degrees':90}]} if len(sizes)==1
                else {'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call)
        self.assertEqual(sizes[1],(1000,116))

    async def test_native_schedule_partition_skips_model_discovery_and_keeps_whole_canvas(self):
        labels=[];rows=[]
        for i,y in enumerate(range(800,0,-100)):
            labels.extend([{'id':f't{i}','text':f'L{i}','x':500,'y':y,'height':10},
                           {'id':f'r{i}','text':'MCB-1P-10A-6kA','x':200,'y':y,'height':10}])
            rows.append({'id':f't{i}','rating_id':f'r{i}','tag':f'L{i}','rating':'MCB-1P-10A-6kA'})
        native={'view_bounds':[0,-400,1000,1000],'labels':labels,'rows':rows}
        captured=[]
        async def call(path,prompt):
            with Image.open(path) as source:captured.append(source.size)
            return json.dumps({'issues':[]} if 'Kiểm kê ĐỘC LẬP' in prompt else {'devices':[]})
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png';Image.new('RGB',(1000,1000)).save(path)
            await extract_regions(path,'Read',call,preserve_row_context=True,native_evidence=native)
        self.assertEqual(len(captured),4)  # Two branch bands, metering tail and coverage.
        self.assertEqual(captured[-1],(1000,1000))
        self.assertEqual(captured[0][0],1000)
        self.assertGreaterEqual(sum(h for _,h in captured[:-1]),1000)

    async def test_circuit_table_regions_keep_tag_and_load_columns_in_source_frame(self):
        calls = []
        async def call(path, prompt):
            with Image.open(path) as source:
                calls.append(source.size)
            return json.dumps(({'layout_kind':'horizontal_circuit_table','regions':[{'box_2d':[200,150,400,330]}]},
                {'devices':[{'name':'MCB','tag':'L1'}], 'boxes':[
                    {'device_id':'0','symbol_box_2d':[100,200,200,300]}]},
                {'issues':[]})[len(calls)-1])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.png'
            Image.new('RGB',(1000,1000),'white').save(path)
            result=await extract_regions(path,'Read',call)
        self.assertEqual(calls[1],(1000,1000))
        self.assertEqual(result['boxes'][0]['symbol_box_2d'],[100,200,200,300])

    def test_explicit_source_type_survives_a_vietnamese_breaker_category(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row = normalize_scoped_row({'category': 'Aptomat chống dòng rò', 'name': 'Aptomat',
                                   'spec': '2P 20A 6kA', 'observed_text': 'RCBO 2P 20A 6KA'})
        self.assertEqual(row['category'], 'RCBO')

    async def test_dol_assembly_is_retained_when_provider_calls_it_a_functional_block(self):
        call = AsyncMock(side_effect=[json.dumps(v) for v in (
            {'regions': []}, {'devices': [{'name': 'DOL', 'spec': 'DOL', 'observed_text': 'DOL',
                'record_kind': 'functional_block', 'quantity': 1}]}, {'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'; Image.new('RGB', (100, 100)).save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(result['devices'][0]['record_kind'], 'assembly')
        self.assertEqual(result['devices'][0]['quantity'], 1)

    def test_inverse_quarter_turn_and_crop_mapping(self):
        self.assertEqual(map_box([100, 200, 300, 400], [200, 400, 800, 1000]), [260, 520, 380, 640])
        self.assertEqual(map_box([100, 200, 300, 400], [0, 0, 1000, 1000], 90), [600, 100, 800, 300])
        original = [100, 200, 300, 400]
        for angle in (90, 180, 270):
            rotated = map_box(original, [0, 0, 1000, 1000], angle)
            self.assertEqual(map_box(rotated, [0, 0, 1000, 1000], 360-angle), original)

    @patch('app.services.ai.source_issue_review.adjudicate_issues', new=keep_disputes)
    async def test_quantity_recovery_preserves_notes_and_maps_ids(self):
        scan = {'regions': [{'box_2d': [500, 0, 1000, 1000]}], 'inventory': [{'name': 'PSU', 'quantity': 6}]}
        first = {'devices': [{'name': 'PSU', 'quantity': 1}, {'name': 'BMS', 'record_kind': 'external_interface'}, {'name': 'Vỏ tủ điện', 'category': 'ENCLOSURE'}],
                 'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]}
        corrected = {'devices': [{'name': 'PSU', 'quantity': 6}, {'name': 'BMS', 'record_kind': 'external_interface'}, {'name': 'Vỏ tủ điện', 'category': 'ENCLOSURE'}],
                     'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]}
        call = AsyncMock(side_effect=[json.dumps(v) for v in (scan, first,
            {'issues': [{'region_id': '0', 'reason': '6 PSU symbols, not 1'}]}, corrected, {'issues': []})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'
            Image.new('RGB', (1000, 1000), 'white').save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(len(result['devices']), 1)
        self.assertEqual(result['devices'][0]['quantity'], 6)
        self.assertEqual(result['boxes'][0]['symbol_box_2d'], [543, 100, 594, 200])
        obs = result['devices'][0]['source_observations']
        self.assertEqual(obs['coverage_review']['status'], 'passed')
        self.assertEqual(obs['panel_notes'][0]['name'], 'BMS')
        self.assertEqual(call.await_count, 5)

    @patch('app.services.ai.source_issue_review.adjudicate_issues', new=keep_disputes)
    async def test_failed_repair_retains_read_rows_and_unresolved_state(self):
        call = AsyncMock(side_effect=[json.dumps(v) for v in (
            {'regions': []}, {'devices': [{'name': 'DOL', 'quantity': 1}]},
            {'issues': [{'region_id': '0', 'reason': 'Missing timer'}]}, {},
            {'issues': [{'region_id': '0', 'reason': 'Still missing timer'}]})])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.png'; Image.new('RGB', (100, 100)).save(path)
            result = await extract_regions(path, 'Read', call)
        self.assertEqual(result['devices'][0]['name'], 'DOL')
        self.assertEqual(result['devices'][0]['source_observations']['coverage_review']['status'], 'needs_review')

    def test_dol_per_branch_never_sizes_overload_from_breaker(self):
        scope = {'source_file_id': 1, 'source_page': 1, 'panel_code': 'MDB'}
        devices = [{**scope, 'category': 'MCB', 'name': 'MCB', 'tag': 'Q1', 'spec': 'MCB3P25A6kA', 'in_a': 25},
                   {**scope, 'category': 'MCB', 'name': 'MCB', 'tag': 'Q2', 'spec': 'MCB3P20A6kA', 'in_a': 20},
                   {**scope, 'name': 'DOL', 'upstream_device': 'Q1', 'connected_load': 'Quạt hút'},
                   {**scope, 'name': 'Khởi động trực tiếp', 'upstream_device': 'Q2', 'connected_load': 'Quạt gió tươi'}]
        enrich_motor_starters(devices)
        first, second = [d['source_observations']['motor_starter'] for d in devices[2:]]
        self.assertEqual(first['upstream']['in_a'], 25)
        self.assertEqual(second['upstream']['in_a'], 20)
        self.assertEqual(len(first['missing_inputs']), 4)
        self.assertTrue(all(c['spec'] is None and c['included_in_total'] is False for c in first['components']))
        self.assertNotIn('MCB', [c['category'] for c in first['components']])
        devices[2]['upstream_device'] = 'missing'
        enrich_motor_starters(devices)
        self.assertIsNone(devices[2]['source_observations']['motor_starter']['upstream'])
        devices[2].pop('upstream_device')
        devices[0]['connected_load'] = 'Quạt hút'
        enrich_motor_starters(devices)
        self.assertEqual(devices[2]['source_observations']['motor_starter']['upstream_status'], 'candidate')
        devices[2]['evidence_region'] = devices[0]['evidence_region'] = {'load_verified': True}
        enrich_motor_starters(devices)
        self.assertEqual(devices[2]['source_observations']['motor_starter']['upstream_status'], 'verified')

    def test_dor_is_not_a_global_alias_and_explicit_motor_input_survives(self):
        devices = [{'name': 'DOR', 'spec': ''}, {'name': 'DOL', 'source_observations': {'circuit': {'motor_rated_current_a': 12}}}]
        enrich_motor_starters(devices)
        self.assertNotIn('source_observations', devices[0])
        self.assertEqual(len(devices[1]['source_observations']['motor_starter']['missing_inputs']), 3)

    def test_overlapping_regions_do_not_merge_repeated_tags_at_distinct_positions(self):
        row = {'category': 'MCB', 'name': 'MCB', 'tag': 'L4', 'spec': '20A', 'quantity': 1}
        parts = [{'devices': [dict(row)], 'boxes': [{'device_id': '0', 'symbol_box_2d': [100, 100, 200, 200]}]},
                 {'devices': [{**row, 'name': 'Aptomat tép', 'category': 'Aptomat tép', 'spec': 'MCB 20A'}, dict(row)], 'boxes': [
                     {'device_id': '0', 'symbol_box_2d': [101, 101, 201, 201]},
                     {'device_id': '1', 'symbol_box_2d': [100, 300, 200, 400]}]}]
        deduplicate_parts(parts)
        self.assertEqual([len(p['devices']) for p in parts], [1, 1])
        self.assertEqual(parts[1]['boxes'][0]['device_id'], '0')
        self.assertEqual(parts[1]['boxes'][0]['symbol_box_2d'], [100, 300, 200, 400])

    async def test_shared_header_requires_independent_relationship_confirmation(self):
        from app.services.ai.device_crop_audit import audit_device_previews
        from app.services.ai.evidence_crops import apply_verified_boxes
        from app.schemas.ai import ExtractedDeviceSchema
        d = ExtractedDeviceSchema(name='MCB', category='MCB', spec='1P20A')
        proposal = {'device_id': '0', 'verified': True, 'symbol_verified': True,
                    'symbol_box_2d': [100, 600, 200, 700], 'text_box_2d': [100, 100, 200, 200],
                    'shared_label': True, 'relationship_evidence': 'Header applies along shared rail'}
        for confirmed in (False, True):
            call = AsyncMock(return_value=json.dumps({'checks': [{'device_id': '0', 'matches': True,
                'symbol_complete': True, 'label_complete': True, 'isolated': True,
                'shared_label_matches': confirmed, 'reason': 'Shared header relation'}]}))
            checked = await audit_device_previews(Image.new('RGB', (1000, 1000), 'white'), call, [d], {'boxes': [proposal]})
            apply_verified_boxes([d], checked, require_symbols=True)
            self.assertEqual(d.evidence_region['status'], 'verified' if confirmed else 'unverified')
            if not confirmed:
                self.assertEqual(d.evidence_region['candidate_region']['symbol_box_2d'], proposal['symbol_box_2d'])
                self.assertIsNone(d.box_2d)

    def test_true_quantity_error_blocks_but_group_representation_does_not(self):
        from app.services.ai.takeoff_verifier import engineering_review
        self.assertFalse(engineering_review({'issues': [{'code': 'wrong_quantity', 'detail': 'Six PSU symbols, not one'}]})['passed'])
        self.assertTrue(engineering_review({'issues': [{'code': 'quantity_representation'}]})['passed'])

    async def test_omitted_shared_header_flag_cannot_bypass_relationship_audit(self):
        from app.services.ai.device_crop_audit import audit_device_previews
        from app.schemas.ai import ExtractedDeviceSchema
        devices = [ExtractedDeviceSchema(name='RCBO', category='RCBO', spec='2P20A') for _ in range(2)]
        boxes = [{'device_id': str(i), 'verified': True, 'symbol_verified': True,
                  'symbol_box_2d': [100, 400+i*100, 200, 450+i*100],
                  'text_box_2d': [100, 100, 200, 200], 'relationship_evidence': 'Same header group'} for i in range(2)]
        call = AsyncMock(return_value=json.dumps({'checks': [{'device_id': str(i), 'matches': True,
            'symbol_complete': True, 'label_complete': True, 'isolated': True} for i in range(2)]}))
        result = await audit_device_previews(Image.new('RGB', (1000, 1000), 'white'), call, devices, {'boxes': boxes})
        self.assertTrue(all(b['shared_label'] for b in result['boxes']))
        self.assertTrue(all(b['verified'] is False for b in result['boxes']))

    def test_quotation_keeps_dol_as_one_set_and_does_not_price_unknown_quantity(self):
        from app.services.ai.procurement_review import build_quotation_rows
        rows = build_quotation_rows([
            {'category': 'DOL', 'name': 'DOL', 'spec': '', 'unit': 'Bộ', 'quantity': 1, 'panel_code': 'MDB'},
            {'category': 'CT', 'name': 'CT', 'spec': '', 'quantity': 1, 'unit': 'Cụm', 'panel_code': 'MDB',
             'quantity_review': {'status': 'needs_review', 'blocking': True}}], [], refresh_prices=False)
        dol = next(r for r in rows if r.get('category') == 'DOL')
        self.assertEqual((dol['quantity'], dol['unit']), (1, 'Bộ'))
        self.assertEqual(dol['source_observations']['motor_starter']['pricing_basis'], 'assembly_only')
        self.assertFalse(any(r.get('category') in {'CONTACTOR', 'OVERLOAD_PROTECTION'} for r in rows))
        ct = next(r for r in rows if r.get('category') == 'CT')
        self.assertIsNone(ct['quantity'])
        self.assertIsNone(ct['line_total'])


if __name__ == '__main__':
    unittest.main()

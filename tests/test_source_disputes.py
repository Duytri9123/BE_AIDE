import json
import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import ezdxf
from PIL import Image
from app.services.ai.source_issue_review import adjudicate_issues
from app.services.ai.cad_linked_devices import linked_candidates, merge_confirmed


class SourceDisputeTests(unittest.IsolatedAsyncioTestCase):
    def test_review_quoted_spare_function_is_preserved_without_inventing_a_load(self):
        import copy
        from app.services.ai.source_issue_review import source_function_issues
        parts=[{'devices':[{'connected_load':None,'electrical_function':'Bảo vệ mạch dự phòng'}]}]
        issue={'region_id':'0','field':'connected_load','device_indices':[0],
            'reason':"Bỏ trống connected_load, trong khi nguồn ghi tải/chức năng là 'DỰ PHÒNG'"}
        checked=copy.deepcopy(parts)
        self.assertEqual(source_function_issues(checked,[issue]),[])
        self.assertIsNone(checked[0]['devices'][0]['connected_load'])
        self.assertEqual(checked[0]['devices'][0]['source_observations']['source_function'],'DỰ PHÒNG')
        for reason in ("Không phải 'DỰ PHÒNG', là 'BƠM 01'", "Nhánh dự phòng thực tế đấu tới 'BƠM 01'"):
            disputed={**issue,'reason':reason}
            self.assertEqual(source_function_issues(copy.deepcopy(parts),[disputed]),[disputed])

    async def test_existing_rating_does_not_resolve_a_missing_neighbour_device(self):
        parts=[{'devices':[{'name':'RCBO','tag':'P19','spec':'2P 20A 6kA','quantity':1}],
                'boxes':[],'notes':[]}]
        issue={'region_id':'0','field':'devices','device_indices':[0],
            'reason':'Thiếu thiết bị RCBO lộ P20, dùng chung nhãn với P19'}
        call=AsyncMock(return_value=json.dumps({'decision':'candidate_correct','observed_text':'RCBO 2P 20A 6kA',
            'confirmed_values':[{'device_index':0,'field':'spec','value':'2P 20A 6kA'}]}))
        remaining,_=await adjudicate_issues(Image.new('RGB',(100,100)),
            [{'box_2d':[0,0,1000,1000]}],parts,[issue],call)
        self.assertEqual(remaining,[issue])

    async def test_existence_dispute_cannot_crop_away_the_candidate_symbol(self):
        seen=[]
        async def call(path,prompt):
            with Image.open(path) as source:seen.append(source.size)
            return json.dumps({'decision':'candidate_correct','observed_text':'CT trên đường nguồn',
                'confirmed_values':[{'device_index':0,'field':'spec','value':''}]})
        parts=[{'devices':[{'name':'CT','spec':''}],
            'boxes':[{'device_id':'0','symbol_box_2d':[210,490,225,500],
                'text_box_2d':[210,490,225,500]}],'notes':[]}]
        issues=[{'region_id':'0','field':'spec','device_indices':[0],
            'reason':'Không thấy CT; chỉ thấy AS','box_2d':[208,526,233,570]}]
        remaining,_=await adjudicate_issues(Image.new('RGB',(1000,1000)),
            [{'box_2d':[50,460,330,620]}],parts,issues,call)
        self.assertEqual(remaining,[]);self.assertGreater(seen[0][0],100)

    def test_repeated_source_wording_is_not_a_duplicate_inventory_row(self):
        from app.services.ai.source_issue_review import is_inventory_duplicate_issue
        from app.services.ai.native_source_review import adjudicate_native_fields
        evidence={'labels':[{'id':'tag','text':'BT2'},{'id':'rating','text':'MCB 1P 32A 6kA'},
            {'id':'load','text':'BẾP ĐIỆN 01'}],
            'rows':[{'id':'tag','rating_id':'rating','tag':'BT2','rating':'MCB 1P 32A 6kA'}]}
        row={'tag':'BT2','connected_load':'BẾP ĐIỆN 01','source_evidence_ids':['tag','rating'],
            'source_observations':{'circuit':{'source':'cad_row','evidence_ids':['load']}}}
        parts=[{'devices':[row]}]
        issue={'region_id':'0','device_indices':[0],'field':'connected_load',
            'reason':'BT2 phải là BẾP ĐIỆN 02, tuy bản vẽ có thể lặp chữ BẾP ĐIỆN 01'}
        self.assertFalse(is_inventory_duplicate_issue(issue))
        remaining,proof=adjudicate_native_fields(evidence,parts,[issue])
        self.assertEqual(remaining,[]);self.assertEqual(proof[0]['observed_text'],'BẾP ĐIỆN 01')
        for reason in ('Thiết bị bị kê lặp lại ở hai vùng','Device listed twice','Duplicate row'):
            self.assertTrue(is_inventory_duplicate_issue({**issue,'reason':reason}))

    async def test_disputed_tag_context_includes_the_actual_tag_and_load_wire(self):
        seen=[]
        async def call(path,prompt):
            with Image.open(path) as source:seen.append(source.size)
            return json.dumps({'decision':'candidate_correct','observed_text':'P1, BƠM 01',
                'confirmed_values':[{'device_index':0,'field':'tag','value':'P1'}]})
        parts=[{'devices':[{'name':'MCB','tag':'P1','connected_load':'BƠM 01'}],
                'boxes':[{'device_id':'0','symbol_box_2d':[100,100,120,150],
                    'tag_box_2d':[100,400,120,440],'load_box_2d':[100,850,120,950]}],'notes':[]}]
        issue={'region_id':'0','field':'tag','device_indices':[0],'reason':'Kiểm tra mã lộ P1',
            'box_2d':[80,100,100,150]}
        remaining,_=await adjudicate_issues(Image.new('RGB',(1000,1000)),
            [{'box_2d':[0,0,1000,1000]}],parts,[issue],call)
        self.assertEqual(remaining,[]);self.assertGreater(seen[0][0],850)

    def test_absent_circuit_code_does_not_need_an_invented_tag_for_consistency(self):
        from app.services.ai.source_issue_review import source_function_issues
        parts=[{'devices':[{'tag':None,'connected_load':'MẠCH ĐIỀU KHIỂN'}]}]
        issue={'region_id':'0','field':'tag','device_indices':[0],
            'reason':'Nhánh không có mã lộ (TÊN LỘ trống), cần kiểm tra tính nhất quán với nhãn mạch'}
        self.assertEqual(source_function_issues(parts,[issue]),[])
        for change in ({'reason':'TÊN LỘ trống nhưng nhãn P6 đọc rõ; cần kiểm tra nhất quán'},
                       {'field':'quantity'},{'device_indices':[1]}):
            disputed={**issue,**change}
            self.assertEqual(source_function_issues(parts,[disputed]),[disputed])
        parts[0]['devices'][0]['tag']='MCB-2P'
        self.assertEqual(source_function_issues(parts,[issue]),[issue])

    async def test_correct_rating_cannot_dismiss_a_vietnamese_repeated_row_issue(self):
        parts=[{'devices':[{'name':'MCB','spec':'16A','quantity':1}], 'boxes':[],'notes':[]}]
        provider=AsyncMock(return_value=json.dumps({'decision':'candidate_correct','observed_text':'16A',
            'confirmed_values':[{'device_index':0,'field':'spec','value':'16A'}]}))
        issue={'region_id':'0','field':'spec','device_indices':[0],'reason':'Thiết bị bị kê lặp lại ở hai vùng'}
        remaining,_=await adjudicate_issues(Image.new('RGB',(100,100)),[{'box_2d':[0,0,1000,1000]}],parts,[issue],provider)
        self.assertEqual(remaining,[issue]);provider.assert_not_awaited()

    def test_spare_function_does_not_require_a_connected_load(self):
        from app.services.ai.source_issue_review import source_function_issues
        parts=[{'devices':[{'connected_load':None,'electrical_function':'Nhánh dự phòng'},
                           {'connected_load':None,'electrical_function':'Nhánh chưa xác định'}]}]
        issue={'region_id':'0','field':'connected_load','device_indices':[0],
               'reason':'Thiếu connected_load DỰ PHÒNG'}
        self.assertEqual(source_function_issues(parts,[issue]),[])
        for changed in ({'device_indices':[1]},{'device_indices':[0,1]},
                        {'field':'quantity'},{'device_indices':[]}):
            disputed={**issue,**changed}
            self.assertEqual(source_function_issues(parts,[disputed]),[disputed])
        disputed={**issue,'field':'tag','reason':'Nhánh dự phòng thiếu nhãn lộ P5'}
        self.assertEqual(source_function_issues(parts,[disputed]),[disputed])

    def test_native_review_requires_the_disputed_field_and_unique_source_identity(self):
        from app.services.ai.native_source_review import adjudicate_native_fields
        evidence={'labels':[{'id':'tag','text':'BT2'}, {'id':'rating','text':'MCB-1P-32A-6kA'},
            {'id':'load','text':'BẾP ĐIỆN 01'}],
            'rows':[{'id':'tag','rating_id':'rating','tag':'BT2','rating':'MCB-1P-32A-6kA'}]}
        row={'tag':'BT2','spec':'1P 32A 6kA','connected_load':'BẾP ĐIỆN 01',
            'source_evidence_ids':['tag','rating'],'source_observations':{
                'circuit':{'source':'cad_row','evidence_ids':['tag','rating','load']}}}
        issue={'region_id':'0','field':'connected_load','device_indices':[0],
               'reason':'Candidate must say BẾP ĐIỆN 02'}
        remaining,proof=adjudicate_native_fields(evidence,[{'devices':[row]}],[issue])
        self.assertEqual(remaining,[])
        self.assertEqual(proof[0]['observed_text'],'BẾP ĐIỆN 01')
        for changed in ({'connected_load':'BẾP ĐIỆN 02'}, {'source_evidence_ids':[]},
                {'source_observations':{'circuit':{'source':'cad_row','evidence_ids':['rating']}}}):
            remaining,_=adjudicate_native_fields(evidence,[{'devices':[{**row,**changed}]}],[issue])
            self.assertEqual(remaining,[issue])
        for changed in ({'field':'quantity'}, {'device_indices':[]}, {'reason':'duplicate row'}):
            disputed={**issue,**changed}
            remaining,_=adjudicate_native_fields(evidence,[{'devices':[row]}],[disputed])
            self.assertEqual(remaining,[disputed])

    async def test_matching_rating_does_not_resolve_a_missing_branch_tag(self):
        for tag,field,expected in ((None,'spec',True),('P1','tag',False)):
            parts=[{'devices':[{'name':'MCB','spec':'16A','quantity':1,'tag':tag}], 'boxes':[],'notes':[]}]
            answer={'decision':'candidate_correct','observed_text':'P1 MCB 16A',
                    'confirmed_values':[{'device_index':0,'field':field,'value':'16A' if field=='spec' else 'P1'}]}
            remaining,_=await adjudicate_issues(Image.new('RGB',(100,100)),[{'box_2d':[0,0,1000,1000]}],parts,
                [{'region_id':'0','field':'tag','device_indices':[0],'reason':'Nhãn lộ P1 cần đối chiếu'}],
                AsyncMock(return_value=json.dumps(answer)))
            self.assertEqual(bool(remaining),expected)

    async def test_failed_dispute_joins_peers_before_removing_source_images(self):
        import asyncio
        started = asyncio.Event()
        cancelled = []
        async def call(path, prompt):
            if Path(path).stem == '0':
                await started.wait()
                raise RuntimeError('provider unavailable')
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(Path(path).is_file())
        issues = [{'region_id': '0', 'reason': 'Check first'}, {'region_id': '0', 'reason': 'Check second'}]
        with self.assertRaisesRegex(RuntimeError, 'provider unavailable'):
            await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}],
                [{'devices': [], 'boxes': [], 'notes': []}], issues, call, concurrency=2)
        self.assertEqual(cancelled, [True])

    def test_repeated_note_reference_is_not_a_duplicate_material(self):
        from app.services.ai.regional_takeoff import repeated_note_reference
        parts=[{'devices':[{'observed_text':'MỖI LỘ 1 NÚT ẤN\n9 NÚT ẤN','quantity':9}],
                'notes':[{'record_kind':'functional_block','observed_text':'MỖI LỘ 1 NÚT ẤN [9 NÚT ẤN]'}]}]
        issue={'reason':'MỖI LỘ 1 NÚT ẤN / 9 NÚT ẤN trùng lặp tại notes của vùng 1','device_indices':[]}
        self.assertTrue(repeated_note_reference(issue,parts))
        self.assertFalse(repeated_note_reference({**issue,'device_indices':[0]},parts))
        self.assertFalse(repeated_note_reference({'reason':'Thiết bị bị trùng giữa hai vùng','device_indices':[]},parts))
        self.assertFalse(repeated_note_reference({**issue,'reason':'GHI CHÚ KHÁC trùng lặp tại notes của vùng 1'},parts))

    def test_final_verifier_receives_source_facts_without_embedded_images(self):
        from app.services.ai.takeoff_verifier import source_interpretation
        fact=source_interpretation({'source_observations':{'group_annotation':{'kind':'shared_rating',
            'branch_tags':['X1','X2'],'observed':'Repeated common header','evidence_image':'data:image/png;base64,secret'},
            'panel_notes':[{'evidence_image':'data:image/png;base64,other'}]}})
        self.assertEqual(fact['group_annotation']['branch_tags'],['X1','X2'])
        self.assertNotIn('base64',json.dumps(fact))
    async def test_recovery_reads_local_pixels_and_maps_them_back_to_the_source(self):
        from app.schemas.ai import ExtractedDeviceSchema
        from app.services.ai.takeoff_evidence_completion import complete_evidence
        device = ExtractedDeviceSchema(name='Timer',category='TIMER',spec='24H');sizes=[]
        async def call(path,prompt):
            with Image.open(path) as crop:sizes.append(crop.size)
            return json.dumps({'boxes':[{'device_id':'0','verified':True,'symbol_verified':True,
                'symbol_box_2d':[500,500,600,600],'text_box_2d':[500,500,600,600]}]})
        async def audit(image,provider,devices,payload,**kwargs):return payload
        with patch('app.services.ai.device_crop_audit.audit_device_previews',new=audit):
            result=await complete_evidence(Image.new('RGB',(1000,1000)),'unused.png',[device],
                {'boxes':[{'device_id':'0','verified':False,'symbol_box_2d':[600,400,620,420]}]},call)
        self.assertEqual(sizes,[(180,180)])
        self.assertEqual(result['boxes'][0]['symbol_box_2d'],[610,410,628,428])

    async def test_failed_local_recovery_can_fall_back_to_the_whole_source(self):
        from app.schemas.ai import ExtractedDeviceSchema
        from app.services.ai.takeoff_evidence_completion import complete_evidence
        device=ExtractedDeviceSchema(name='Timer',category='TIMER',spec='24H');sizes=[]
        async def call(path,prompt):
            with Image.open(path) as crop:sizes.append(crop.size)
            return '{"boxes":[]}'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'full.png';image=Image.new('RGB',(1000,1000));image.save(path)
            result=await complete_evidence(image,path,[device],{'boxes':[{'device_id':'0','verified':False,
                'symbol_box_2d':[600,400,620,420]}]},call)
        self.assertEqual(sizes,[(180,180),(1000,1000)])
        self.assertFalse(result['boxes'][0]['verified'])
        self.assertEqual(result['boxes'][0]['symbol_box_2d'],[600,400,620,420])

    async def test_local_repair_keeps_distant_tag_anchor_for_independent_reaudit(self):
        from app.schemas.ai import ExtractedDeviceSchema
        from app.services.ai.takeoff_evidence_completion import complete_evidence
        device = ExtractedDeviceSchema(name='MCB', category='MCB', spec='', tag='L1')
        call = AsyncMock(return_value=json.dumps({'boxes': [{'device_id': '0', 'verified': True,
            'symbol_verified': True, 'symbol_box_2d': [500,500,600,600], 'text_box_2d': [500,500,600,600]}]}))
        seen = []
        async def audit(image, provider, devices, payload, **kwargs):
            box = payload['boxes'][0]
            seen.append(box['tag_box_2d'])
            box['tag_matches'] = True
            return payload
        with patch('app.services.ai.device_crop_audit.audit_device_previews', new=audit):
            result = await complete_evidence(Image.new('RGB',(1000,1000)), 'unused.png', [device],
                {'boxes': [{'device_id': '0', 'verified': False, 'symbol_box_2d': [600,400,620,420],
                            'tag_box_2d': [800,800,850,850]}]}, call)
        self.assertEqual(seen, [[800,800,850,850]])
        self.assertEqual(call.await_count, 1)
        # The distant tag makes a local symbol-only repair insufficient; use
        # the whole source, keeping the provider's source-frame coordinates.
        self.assertEqual(result['boxes'][0]['symbol_box_2d'], [500,500,600,600])

    def test_source_overlap_does_not_clip_the_target_at_a_neighbour_boundary(self):
        from app.services.ai.evidence_preview import device_preview
        image = Image.new('RGB', (1000, 1000), 'white')
        image.paste('blue', (199, 110, 202, 140))
        preview = device_preview(image, {'symbol_box_2d': [100, 100, 150, 201],
            'neighbor_symbol_boxes_2d': [[100, 200, 150, 250]]}, tight=True)[0]
        crop = Image.open(io.BytesIO(base64.b64decode(preview['evidence_image'].split(',')[1])))
        self.assertIn((0, 0, 255), list(crop.getdata()))

    async def test_overlap_can_pass_only_with_clear_source_identity(self):
        from app.schemas.ai import ExtractedDeviceSchema
        from app.services.ai.device_crop_audit import audit_device_previews
        device = ExtractedDeviceSchema(name='MCB', category='MCB', spec='20A')
        proposal = {'device_id': '0', 'verified': True, 'symbol_verified': True,
                    'symbol_box_2d': [100, 100, 150, 150], 'text_box_2d': [100, 140, 150, 200]}
        for source_overlap, clear, expected in ((True, True, True), (True, False, False), (False, True, True)):
            call = AsyncMock(return_value=json.dumps({'checks': [{'device_id': '0', 'matches': True,
                'symbol_complete': True, 'label_complete': True, 'isolated': False,
                'source_overlap': source_overlap, 'identity_unambiguous': clear}]}))
            checked = await audit_device_previews(Image.new('RGB', (1000,1000),'white'),call,[device],{'boxes':[proposal]})
            self.assertEqual(checked['boxes'][0]['verified'], expected)

    def test_unnamed_observations_are_not_merged_only_because_the_boxes_overlap(self):
        from app.services.ai.regional_takeoff import deduplicate_parts
        parts = [{'devices': [{'category':'MCB','spec':'20A','quantity':1}],
                  'boxes':[{'device_id':'0','symbol_box_2d':[100,100,200,200]}]} for _ in range(2)]
        deduplicate_parts(parts)
        self.assertEqual(sum(len(p['devices']) for p in parts),2)

    async def test_local_quantity_confirmation_does_not_clear_global_duplicate(self):
        parts = [{'devices': [{'quantity': 1}], 'boxes': [], 'notes': []}]
        call = AsyncMock()
        issues, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'Thiết bị bị trùng ở hai vùng'}], call)
        self.assertEqual(len(issues), 1)
        self.assertEqual(call.await_count, 0)

    async def test_functional_note_confirmation_stays_a_note(self):
        parts = [{'devices': [], 'boxes': [], 'notes': [{'name': 'MDK', 'record_kind': 'functional_block'}]}]
        answer = {'decision': 'candidate_correct', 'observed_text': 'MDK',
                  'confirmed_notes': [{'note_index': 0, 'record_kind': 'functional_block'}]}
        issues, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'note_indices': [0], 'reason': 'Verify block'}], AsyncMock(return_value=json.dumps(answer)))
        self.assertEqual(issues, [])
        self.assertEqual(parts[0]['devices'], [])
        self.assertEqual(parts[0]['notes'][0]['verification_status'], 'verified')
        self.assertEqual(parts[0]['notes'][0]['record_kind'], 'functional_block')

    async def test_dol_is_not_reclassified_out_of_the_assembly_inventory(self):
        parts = [{'devices': [{'name': 'DOL', 'spec': 'DOL', 'record_kind': 'assembly'}], 'boxes': [], 'notes': []}]
        answer = {'decision': 'candidate_wrong', 'observed_text': 'DOL',
                  'classification': {'device_index': 0, 'record_kind': 'functional_block'}}
        issues, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'Verify block'}], AsyncMock(return_value=json.dumps(answer)))
        self.assertEqual(len(issues), 1)
        self.assertEqual(len(parts[0]['devices']), 1)

    async def test_explicit_nine_button_note_is_not_replaced_by_six_branches(self):
        parts = [{'devices': [{'name': 'Nút ấn', 'quantity': 9, 'observed_text': '9 NÚT ẤN'}], 'boxes': [], 'notes': []}]
        call = AsyncMock(return_value=json.dumps({'decision': 'candidate_correct', 'observed_text': '9 NÚT ẤN',
             'confirmed_values': [{'device_index': 0, 'field': 'quantity', 'value': 9}]}))
        remaining, notes = await adjudicate_issues(Image.new('RGB', (1000, 1000)), [{'box_2d': [0, 0, 1000, 1000]}],
             parts, [{'region_id': '0', 'reason': 'Only six branches'}], call)
        self.assertEqual(remaining, [])
        self.assertEqual(parts[0]['devices'][0]['quantity'], 9)
        self.assertEqual(notes[0]['verification_status'], 'verified')

    async def test_wrong_value_or_no_observed_source_cannot_clear_dispute(self):
        for answer in ({'decision': 'candidate_correct', 'observed_text': '6',
                        'confirmed_values': [{'device_index': 0, 'field': 'quantity', 'value': 6}]},
                       {'decision': 'candidate_correct', 'observed_text': '',
                        'confirmed_values': [{'device_index': 0, 'field': 'quantity', 'value': 9}]}):
            parts = [{'devices': [{'quantity': 9}], 'boxes': [], 'notes': []}]
            remaining, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}],
                parts, [{'region_id': '0', 'reason': 'Dispute'}], AsyncMock(return_value=json.dumps(answer)))
            self.assertEqual(len(remaining), 1)

    async def test_matching_rating_does_not_clear_a_wrong_quantity(self):
        parts = [{'devices': [{'quantity': 1, 'spec': '2P20A'}], 'boxes': [], 'notes': []}]
        answer = {'decision': 'candidate_correct', 'observed_text': 'RCBO 2P20A',
                  'confirmed_values': [{'device_index': 0, 'field': 'spec', 'value': '2P20A'}]}
        remaining, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'Sai số lượng, cần hai cái'}], AsyncMock(return_value=json.dumps(answer)))
        self.assertEqual(len(remaining), 1)

    async def test_functional_block_moves_to_verified_notes_without_losing_box_ids(self):
        parts = [{'devices': [{'name': 'MDK'}, {'name': 'Timer'}], 'boxes': [{'device_id': '1', 'symbol_box_2d': [10, 20, 30, 40]}], 'notes': []}]
        call = AsyncMock(return_value=json.dumps({'decision': 'candidate_wrong', 'observed_text': 'MẠCH ĐIỀU KHIỂN',
             'classification': {'device_index': 0, 'record_kind': 'functional_block'}}))
        issues, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'MDK not a purchased controller'}], call)
        self.assertEqual(issues, [])
        self.assertEqual(parts[0]['devices'], [{'name': 'Timer'}])
        self.assertEqual(parts[0]['boxes'][0]['device_id'], '0')
        self.assertEqual(parts[0]['notes'][0]['record_kind'], 'functional_block')

    async def test_one_confirmed_row_does_not_clear_a_multirow_dispute(self):
        parts = [{'devices': [{'quantity': 1}, {'quantity': 1}], 'boxes': [], 'notes': []}]
        answer = {'decision': 'candidate_correct', 'observed_text': '1 cái',
                  'confirmed_values': [{'device_index': 0, 'field': 'quantity', 'value': 1}]}
        remaining, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'Sai số lượng ở hai dòng', 'device_indices': [0, 1]}],
             AsyncMock(return_value=json.dumps(answer)))
        self.assertEqual(len(remaining), 1)

    async def test_classification_of_an_unrequested_row_cannot_remove_it(self):
        parts = [{'devices': [{'name': 'MCB'}, {'name': 'MDK'}], 'boxes': [], 'notes': []}]
        answer = {'decision': 'candidate_wrong', 'observed_text': 'MDK',
                  'classification': {'device_index': 1, 'record_kind': 'functional_block'}}
        remaining, _ = await adjudicate_issues(Image.new('RGB', (100, 100)), [{'box_2d': [0, 0, 1000, 1000]}], parts,
             [{'region_id': '0', 'reason': 'Sai dòng MCB', 'device_indices': [0]}], AsyncMock(return_value=json.dumps(answer)))
        self.assertEqual(len(remaining), 1)
        self.assertEqual(len(parts[0]['devices']), 2)

    def test_native_line_across_six_branches_is_not_a_two_pole_device(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'source.dxf'; doc = ezdxf.new(); model = doc.modelspace()
            model.add_lwpolyline([(15, 50), (65, 50)])
            model.add_lwpolyline([(65, 50, 0, 2), (62, 50, 2, 2)], format='xyse'); doc.saveas(path)
            rows = [{'category': 'RCBO', 'poles': 2, 'spec': '2P25A', 'quantity': 1, 'tag': f'P{i}'} for i in range(6)]
            boxes = [{'device_id': str(i), 'geometry_source': 'native_cad_block_and_rotated_text',
                      'symbol_box_2d': [450, 100+i*100, 550, 150+i*100], 'text_box_2d': [450, 0, 550, 90],
                      'tag_box_2d': [800, 100+i*100, 900, 150+i*100]} for i in range(6)]
            with patch('app.services.ingestion.cad_source_evidence.cad_evidence', return_value={'view_bounds': [0, 0, 100, 100]}):
                candidates = linked_candidates(path, None, rows, boxes)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(len(candidates[0]['members']), 6)
            result, _ = merge_confirmed(rows, boxes, candidates, [{'candidate_id': '0', 'same_device': True,
                'mechanical_link_visible': True, 'shared_spec_visible': True, 'observed': 'line'}])
            self.assertEqual(len(result), 6)

    def test_shared_rating_keeps_two_devices_and_attaches_comparison_proof(self):
        rows = [{'tag': 'X1', 'source_observations': {}}, {'tag': 'X2', 'source_observations': {}}]
        boxes = [{'device_id': str(i)} for i in range(2)]
        candidate = {'members': [0, 1], 'branch_tags': ['X1', 'X2'], 'reference_box_2d': [1, 2, 3, 4]}
        result, evidence = merge_confirmed(rows, boxes, [candidate], [{'candidate_id': '0', 'relation_type': 'shared_rating',
            'same_device': False, 'shared_spec_visible': True, 'observed': 'Same leader spans six separate branches elsewhere'}])
        self.assertEqual(len(result), 2)
        self.assertTrue(all(b['source_annotation'] == 'shared_rating' for b in evidence))

    def test_actual_mechanical_link_requires_explicit_agreement_and_keeps_both_tags(self):
        rows = [{'name': 'RCBO', 'spec': '2P20A', 'poles': 2, 'quantity': 1, 'tag': tag,
                 'source_observations': {}, 'connected_load': tag+' load'} for tag in ['X1', 'X2']]
        candidate = {'members': [0, 1], 'branch_tags': ['X1', 'X2'], 'connector_handles': ['line', 'arrow'],
                     'symbol_box_2d': [1, 2, 30, 40], 'text_box_2d': [1, 1, 30, 2], 'tag_box_2d': [80, 2, 90, 40]}
        decision = {'candidate_id': '0', 'relation_type': 'mechanical_link', 'same_device': True,
                    'mechanical_link_visible': True, 'shared_spec_visible': True, 'observed': 'Two linked poles in source'}
        result, boxes = merge_confirmed(rows, [], [candidate], [decision])
        self.assertEqual((len(result), result[0]['quantity'], result[0]['drawing_quantity']), (1, 1, 2))
        self.assertEqual(result[0]['source_observations']['linked_device']['branch_tags'], ['X1', 'X2'])
        self.assertIsNone(result[0]['tag'])
        self.assertEqual(boxes[0]['symbol_box_2d'], candidate['symbol_box_2d'])
        decision['mechanical_link_visible'] = False
        unchanged, _ = merge_confirmed(rows, [], [candidate], [decision])
        self.assertEqual(len(unchanged), 2)


if __name__ == '__main__':
    unittest.main()

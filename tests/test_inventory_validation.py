import unittest
from app.services.ai.inventory_validation import extract_with_retry, require_inventory, count_mismatches, independent_count_prompt, count_with_retry


class InventoryValidationTests(unittest.IsolatedAsyncioTestCase):
    def test_panel_observation_uses_device_code_without_empty_duplicate(self):
        from app.services.ai.inventory_validation import merge_panel_observations
        devices=require_inventory('{"devices":[{"panel_code":"TĐ-T","category":"CB","name":"Q","quantity":1}]}')
        panels=merge_panel_observations([{'panel_code':'TĐ-T','location':'Tầng 1'}],[{'panel_code':'TĐT','dimension':'1000x600x300','location':''}],devices)
        self.assertEqual(panels,[{'panel_code':'TĐ-T','location':'Tầng 1','dimension':'1000x600x300'}])

    def test_repair_keeps_numeric_fields_from_explicit_breaker_spec(self):
        devices=require_inventory('{"devices":[{"category":"MCCB","name":"Q","spec":"3P 200A 85kA","quantity":1},{"category":"CB","name":"Dự phòng","spec":"CB dự phòng","quantity":1},{"category":"CB","name":"Q2","spec":"10-16A","quantity":1}]}')
        self.assertEqual((devices[0].poles,devices[0].in_a,devices[0].icu_ka),(3,200,85))
        self.assertIsNone(devices[1].in_a)
        self.assertIsNone(devices[2].in_a)

    def test_source_branch_labels_replace_generic_type_tags_only(self):
        devices=require_inventory('{"devices":[{"category":"CB","name":"L12 - Tủ nhánh","tag":"CB","quantity":1},{"category":"CB","name":"L13 - Tủ nhánh","tag":"Q13","quantity":1},{"category":"CB","name":"Dự phòng","tag":"CB","quantity":1}]}')
        self.assertEqual([d.tag for d in devices],['L12','Q13','CB'])

    def test_panel_crop_rejects_overlap_and_out_of_page_coordinates(self):
        from app.services.ai.inventory_validation import require_panel_regions
        with self.assertRaises(ValueError):
            require_panel_regions({'panels':[{'panel_code':'P','box_2d':[-1,0,500,500]}]})
        with self.assertRaises(ValueError):
            require_panel_regions({'panels':[{'panel_code':'P','box_2d':[0,0,500,500]}, {'panel_code':'Q','box_2d':[0,0,500,500]}]})
        self.assertEqual(len(require_panel_regions({'panels':[{'panel_code':'P','box_2d':[0,0,1000,500]}, {'panel_code':'Q','box_2d':[0,500,1000,1000]}]})),2)

    async def test_empty_crop_count_allowed_but_empty_page_rejected(self):
        from unittest.mock import AsyncMock
        self.assertEqual(await count_with_retry(AsyncMock(return_value='{"counts":[]}'), 'Crop', allow_empty=True), {'counts':[]})
        with self.assertRaises(ValueError):
            await count_with_retry(AsyncMock(return_value='{"counts":[]}'), 'Full page')

    def test_fuse_quantity_compares_bodies_not_inventory_rows(self):
        devices=require_inventory('{"devices":[{"panel_code":"P","category":"FUSE","name":"F1","quantity":2}]}')
        self.assertEqual(len(count_mismatches(devices,{'counts':[{'panel_code':'P','category':'FUSE','quantity':1}]})),1)

    def test_equivalent_source_names_are_not_missing_devices(self):
        devices=require_inventory('{"devices":[{"panel_code":"TĐT","category":"Đèn báo","name":"Đèn RYB","quantity":3},{"panel_code":"TĐT","category":"METER","name":"Vôn kế","quantity":1},{"panel_code":"TĐT","category":"SWITCH","name":"Công tắc chọn điện áp","quantity":1}]}')
        self.assertEqual(count_mismatches(devices,{'counts':[{'panel_code':'TĐ-T','category':c,'quantity':q} for c,q in [('INDICATOR',3),('VOLTMETER',1),('SELECTOR',1)]]}),[])

    def test_generic_breaker_or_meter_does_not_gain_unverified_type(self):
        devices=require_inventory('{"devices":[{"panel_code":"P","category":"CB","name":"Q1","quantity":1},{"panel_code":"P","category":"METER","name":"Đồng hồ","quantity":1}]}')
        self.assertTrue(count_mismatches(devices,{'counts':[{'panel_code':'P','category':'MCB','quantity':1},{'panel_code':'P','category':'VOLTMETER','quantity':1}]}))

    def test_unverified_extra_device_is_not_ignored(self):
        devices=require_inventory('{"devices":[{"panel_code":"P","category":"CB","name":"Q1","quantity":1},{"panel_code":"P","category":"TERMINAL","name":"Inferred terminal","quantity":1}]}')
        self.assertEqual(len(count_mismatches(devices,{'counts':[{'panel_code':'P','category':'CB','quantity':1}]})),1)

    async def test_malformed_independent_count_retries_with_new_prompt(self):
        from unittest.mock import AsyncMock
        call=AsyncMock(side_effect=['not JSON','{"counts":[{"panel_code":"TĐT","category":"CB","quantity":20}]}'])
        payload=await count_with_retry(call,'Read source')
        self.assertEqual(payload['counts'][0]['quantity'],20)
        self.assertNotEqual(call.call_args_list[0].args[0],call.call_args_list[1].args[0])

    def test_boolean_is_not_a_source_quantity(self):
        with self.assertRaises(ValueError):
            count_mismatches([],{'counts':[{'panel_code':'P','category':'CB','quantity':True}]})

    def test_count_prompt_preserves_panel_labels_without_leaking_counts(self):
        devices=require_inventory('{"devices":[{"panel_code":"TĐ-BTA","category":"CB","name":"Q1","quantity":987}]}')
        prompt=independent_count_prompt(devices)
        self.assertIn('TĐ-BTA',prompt)
        self.assertNotIn('987',prompt)
        self.assertIn('Nguồn chỉ ghi CB thì dùng CB',prompt)
        self.assertIn('Không đếm một cụm đo lường thành một OTHER',prompt)

    def test_independent_counts_detect_missing_contactor_and_invented_relay(self):
        devices = require_inventory('{"devices":[{"panel_code":"TĐ-PX2","category":"RELAY","name":"MDK","quantity":1}]}')
        result = count_mismatches(devices, {'counts':[
            {'panel_code':'TD PX2','category':'CONTACTOR','quantity':6},
            {'panel_code':'TD PX2','category':'RELAY','quantity':0}]})
        self.assertEqual(len(result), 2)

    def test_counts_sum_multiple_source_groups(self):
        devices = require_inventory('{"devices":[{"panel_code":"PX1","category":"CONTACTOR","name":"C","quantity":12}]}')
        self.assertEqual(count_mismatches(devices, {'counts':[
            {'panel_code':'PX1','category':'CONTACTOR','quantity':6},
            {'panel_code':'PX1','category':'CONTACTOR','quantity':6}]}), [])

    def test_rejects_truncated_inventory(self):
        with self.assertRaises(ValueError):
            require_inventory('{"devices":[{"category":"MCB"')

    async def test_retries_invalid_response(self):
        responses = iter(['{"devices":[', '{"devices":[{"category":"MCB","name":"Q1","quantity":1}]}'])
        prompts = []
        async def call(prompt):
            prompts.append(prompt)
            return next(responses)
        _, devices = await extract_with_retry(call, 'Read source')
        self.assertEqual(len(devices), 1)
        self.assertEqual(len(prompts), 2)

    async def test_never_accepts_repeated_invalid_response(self):
        async def call(prompt):
            return '{"devices":[]}'
        with self.assertRaises(ValueError):
            await extract_with_retry(call, 'Read source')

import unittest
from app.services.ai.inventory_validation import extract_with_retry, require_inventory, count_mismatches


class InventoryValidationTests(unittest.IsolatedAsyncioTestCase):
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

import json
import unittest
from unittest.mock import AsyncMock

from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.inventory_validation import count_mismatches, repair_counted_inventory, recount_ct_symbols, recount_meter_symbols


class CTCountRepairTests(unittest.IsolatedAsyncioTestCase):
    def ct(self, **changes):
        return Device(**(dict(category='CT', name='Biến dòng', spec='Ti 250/5',
                             panel_code='MDB102', quantity=3) | changes))

    def counts(self, quantity=1, panel='MDB102'):
        return {'counts': [dict(panel_code=panel, category='CT', quantity=quantity,
                                evidence='Ti 250/5 (1)')]}

    async def test_screenshot_mismatch_rechecks_only_ct_and_preserves_breaker(self):
        breaker = Device(category='MCCB', name='MCCB', spec='3P 250A',
                         panel_code='MDB102', quantity=1)
        corrected = self.ct(drawing_quantity=1, procurement_quantity=3,
                            quantity_basis='Ký hiệu bộ CT; đường đo thể hiện cả ba pha',
                            technical_analysis='Một CT trên mỗi đường đo pha trong bộ.')
        call = AsyncMock(return_value=json.dumps({'devices': [corrected.model_dump()]}))
        counts = self.counts()
        counts['counts'].append(dict(panel_code='MDB102', category='MCCB', quantity=1))
        _, rows = await repair_counted_inventory(call, 'Read source', [breaker, self.ct()], counts)
        call.assert_awaited_once()
        self.assertIn('CHỈ kiểm tra biến dòng CT', call.call_args.args[0])
        self.assertIn('250/5 là tỷ số dòng', call.call_args.args[0])
        self.assertIs(rows[0], breaker)
        self.assertEqual((rows[1].drawing_quantity, rows[1].quantity,
                          rows[1].procurement_quantity), (1, 3, 3))
        self.assertEqual(count_mismatches(rows, counts), [])
        from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
        AnalysisPipelineService._infer_practical_quantities(rows)
        self.assertEqual(rows[1].quantity, 3)

    async def test_source_can_resolve_to_one_physical_ct(self):
        corrected = self.ct(quantity=1, drawing_quantity=1, procurement_quantity=1,
                            quantity_basis='Nguồn chỉ thể hiện một CT trên một nhánh đo')
        call = AsyncMock(return_value=json.dumps({'devices': [corrected.model_dump()]}))
        _, rows = await repair_counted_inventory(call, 'Read', [self.ct()], self.counts())
        self.assertEqual(rows[0].quantity, 1)

    def test_unexplained_phase_multiplier_does_not_pass(self):
        for changes in ({}, {'drawing_quantity': 1},
                        {'drawing_quantity': 1, 'procurement_quantity': 3},
                        {'drawing_quantity': 1, 'quantity_basis': 'Three phases'}):
            with self.subTest(changes=changes):
                self.assertTrue(count_mismatches([self.ct(**changes)], self.counts()))

    def test_explicit_source_multiplier_and_panel_are_still_constraints(self):
        ct = self.ct(drawing_quantity=1, procurement_quantity=3,
                     quantity_basis='Grouped circuit')
        self.assertTrue(count_mismatches([ct], self.counts(quantity=3)))
        self.assertTrue(count_mismatches([ct], self.counts(panel='MDB101')))
        self.assertEqual(count_mismatches([self.ct(drawing_quantity=3)], self.counts(quantity=3)), [])

    def test_explicit_source_count_survives_material_normalization(self):
        from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
        ct = self.ct(name='3xCT', drawing_quantity=3, procurement_quantity=3,
                     quantity_basis='Nhãn nguồn ghi 3xCT')
        for _ in range(2):
            AnalysisPipelineService._infer_practical_quantities([ct])
            self.assertEqual(count_mismatches([ct], self.counts(quantity=3)), [])
            self.assertEqual((ct.drawing_quantity, ct.quantity), (3, 3))

    async def test_unresolved_ct_remains_visible_for_review_after_bounded_repair(self):
        call = AsyncMock(return_value=json.dumps({'devices': [self.ct().model_dump()]}))
        _,rows=await repair_counted_inventory(call, 'Read', [self.ct()], self.counts(), attempts=1)
        self.assertEqual(rows[0].quantity,3)
        self.assertEqual(rows[0].quantity_review['status'],'needs_review')

    async def test_independent_recount_corrects_inferred_three_without_borrowing_bom(self):
        old = self.counts(quantity=3)
        old['counts'].append(dict(panel_code='MDB102', category='MCCB', quantity=1))
        call = AsyncMock(return_value=json.dumps(self.counts(quantity=1)))
        corrected = await recount_ct_symbols(call, old)
        self.assertEqual(corrected['counts'][0]['category'], 'MCCB')
        self.assertEqual(corrected['counts'][1]['quantity'], 1)
        self.assertEqual(old['counts'][0]['quantity'], 3)
        self.assertNotIn('bóc tách 1', call.call_args.args[0])
        self.assertIn('không phải số CT vật lý', call.call_args.args[0])
        self.assertEqual(corrected['ct_recount']['counts'][0]['quantity'], 1)

    async def test_uncertain_or_wrong_panel_recount_cannot_replace_source_count(self):
        for observed in ({**self.counts(), 'uncertain_regions':['Mờ']},
                         self.counts(panel='OTHER')):
            with self.subTest(observed=observed), self.assertRaises(ValueError):
                await recount_ct_symbols(AsyncMock(return_value=json.dumps(observed)), self.counts(3))

    async def test_meter_function_recount_preserves_other_source_groups(self):
        source = self.counts()
        source['counts'].append(dict(panel_code='MDB102', category='AMMETER', quantity=1, evidence='Connected to CT'))
        observed = {'counts':[dict(panel_code='MDB102',category='METER',quantity=1,evidence='Hộp đồng hồ, không đọc được A/V')], 'uncertain_regions':[]}
        corrected = await recount_meter_symbols(AsyncMock(return_value=json.dumps(observed)), source)
        self.assertEqual([row['category'] for row in corrected['counts']], ['CT', 'METER'])
        self.assertEqual(source['counts'][1]['category'], 'AMMETER')


if __name__ == '__main__':
    unittest.main()

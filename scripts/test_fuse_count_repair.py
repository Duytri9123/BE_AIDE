import json
import unittest
from unittest.mock import AsyncMock
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.inventory_validation import repair_counted_inventory


class FuseCountRepairTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_disputed_fuses_without_replacing_other_devices(self):
        breaker=ExtractedDeviceSchema(category='MCB',name='MCB',spec='2P 20A',panel_code='TDT',quantity=1)
        fuse=ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='',panel_code='TDT',quantity=3)
        call=AsyncMock(return_value=json.dumps({'devices':[{'category':'FUSE','name':'Fuse','spec':'',
            'panel_code':'TDT','quantity':1,'quantity_basis':'Một thân cầu chì có hai đầu nối'}]}))
        counts={'counts':[{'panel_code':'TDT','category':'MCB','quantity':1},
                          {'panel_code':'TDT','category':'FUSE','quantity':1}]}
        _,rows=await repair_counted_inventory(call,'Full inventory',[breaker,fuse],counts)
        call.assert_awaited_once()
        self.assertIs(rows[0],breaker)
        self.assertEqual(rows[1].quantity,1)
        self.assertIn('CHỈ kiểm tra cầu chì',call.call_args.args[0])

    async def test_explicit_group_of_three_is_not_forced_to_one(self):
        fuse=ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='3x2A',panel_code='TDT',quantity=1)
        call=AsyncMock(return_value=json.dumps({'devices':[{'category':'FUSE','name':'Fuse','spec':'3x2A',
            'panel_code':'TDT','quantity':3,'quantity_basis':'Nhãn nguồn ghi 3x2A'}]}))
        _,rows=await repair_counted_inventory(call,'Read',[fuse],{'counts':[{'panel_code':'TDT','category':'FUSE','quantity':3}]})
        self.assertEqual(rows[0].quantity,3)

    async def test_grouped_symbol_keeps_three_circuit_derived_materials(self):
        fuse=ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='',panel_code='TDT',quantity=3)
        call=AsyncMock(return_value=json.dumps({'devices':[{'category':'FUSE','name':'Fuse','spec':'',
            'panel_code':'TDT','quantity':3,'drawing_quantity':1,'procurement_quantity':3,
            'quantity_basis':'Một ký hiệu chung cho bộ bảo vệ ba đường áp L1/L2/L3 trước chuyển mạch',
            'technical_analysis':'Mỗi đường áp pha trước chuyển mạch cần một cầu chì; một bộ gồm ba chiếc.'}]}))
        counts={'counts':[{'panel_code':'TDT','category':'FUSE','quantity':1}]}
        _,rows=await repair_counted_inventory(call,'Read circuit',[fuse],counts)
        self.assertEqual(rows[0].drawing_quantity,1)
        self.assertEqual(rows[0].quantity,3)
        self.assertEqual(rows[0].procurement_quantity,3)
        from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
        AnalysisPipelineService._infer_practical_quantities(rows)
        self.assertEqual(rows[0].quantity,3)
        self.assertIn('ba đường áp',rows[0].quantity_basis)
        from app.services.ai.inventory_validation import count_mismatches
        self.assertEqual(count_mismatches(rows,counts),[])

    def test_material_quantity_without_separate_source_count_still_mismatches(self):
        from app.services.ai.inventory_validation import count_mismatches
        fuse=ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='3P',panel_code='TDT',quantity=3)
        self.assertTrue(count_mismatches([fuse],{'counts':[{'panel_code':'TDT','category':'FUSE','quantity':1}]}))

    async def test_unconfirmed_quantity_keeps_result_and_marks_review(self):
        fuse=ExtractedDeviceSchema(category='FUSE',name='Fuse',spec='',panel_code='TDT',quantity=3)
        call=AsyncMock(return_value=json.dumps({'devices':[{'category':'FUSE','name':'Fuse','spec':'',
            'panel_code':'TDT','quantity':3,'quantity_basis':'Chưa đọc rõ'}]}))
        _,rows=await repair_counted_inventory(call,'Read',[fuse],{'counts':[{'panel_code':'TDT','category':'FUSE','quantity':1}]},attempts=1)
        self.assertEqual(rows[0].quantity,3)
        self.assertEqual(rows[0].quantity_review['independent_group_count'],1)
        self.assertEqual(rows[0].quantity_review['status'],'needs_review')


if __name__ == '__main__':
    unittest.main()

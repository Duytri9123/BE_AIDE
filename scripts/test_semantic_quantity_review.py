import json
import unittest
from unittest.mock import AsyncMock
from app.schemas.ai import ExtractedDeviceSchema as Device
from app.services.ai.inventory_validation import count_mismatches,annotate_quantity_review,repair_counted_inventory

class SemanticQuantityTests(unittest.IsolatedAsyncioTestCase):
    def counts(self,category='INDICATOR',quantity=1):
        return {'counts':[{'panel_code':'P','category':category,'quantity':quantity,'evidence':'Một cụm biểu diễn trên sơ đồ'}]}

    def test_grouped_lamps_can_require_three_physical_parts(self):
        row=Device(category='INDICATOR',name='Đèn báo',spec='R/Y/B',panel_code='P',quantity=3,
            drawing_quantity=1,procurement_quantity=3,quantity_basis='Một cụm có ba đèn R/Y/B trên ba đường pha',
            technical_analysis='Mỗi đường pha có một đèn; cụm này cần ba đèn vật lý.')
        self.assertEqual(annotate_quantity_review([row],self.counts()),[])
        self.assertEqual(row.quantity_review['proposed_quantity'],3)
        self.assertEqual(row.quantity_review['drawing_quantity'],1)
        self.assertEqual(count_mismatches([row],self.counts(quantity=3)),[])

    def test_engineering_assumption_is_kept_pending_even_when_counts_reconcile(self):
        row=Device(category='CT',name='CT',spec='250/5',panel_code='P',quantity=3,
            drawing_quantity=1,procurement_quantity=3,quantity_basis='Đề xuất bộ đo ba pha',
            technical_analysis='Ba CT cho ba pha, còn cần xác nhận cấu hình đo.',
            quantity_review={'status':'needs_review','assumptions':['Đồng hồ đo ba pha']})
        annotate_quantity_review([row],self.counts('CT'))
        self.assertEqual(row.quantity_review['status'],'needs_review')
        self.assertEqual(row.quantity_review['assumptions'],['Đồng hồ đo ba pha'])

    async def test_four_repeated_branches_are_reasoned_instead_of_forced_to_one(self):
        original=Device(category='MCB',name='MCB',spec='1P 10A',panel_code='P',quantity=4)
        corrected={**original.model_dump(),'drawing_quantity':1,'procurement_quantity':4,
            'quantity_basis':'Một nhánh đại diện bốn lộ lặp được nhãn x4 xác định',
            'technical_analysis':'Bốn lộ độc lập, mỗi lộ cần một MCB 1P, không phải nhân theo số cực.'}
        call=AsyncMock(return_value=json.dumps({'devices':[corrected]}))
        _,rows=await repair_counted_inventory(call,'Read source',[original],self.counts('MCB'),attempts=1)
        self.assertEqual(rows[0].quantity,4)
        self.assertEqual(count_mismatches(rows,self.counts('MCB')),[])
        self.assertIn('không phải đáp án vật tư',call.call_args.args[0])

    def test_three_poles_alone_do_not_certify_three_breakers(self):
        row=Device(category='MCCB',name='MCCB',spec='3P',poles=3,panel_code='P',quantity=3,drawing_quantity=1)
        self.assertTrue(annotate_quantity_review([row],self.counts('MCCB')))
        self.assertEqual(row.quantity_review['status'],'needs_review')

    async def test_unreadable_repair_keeps_last_readable_inventory(self):
        row=Device(category='INDICATOR',name='Đèn',spec='',panel_code='P',quantity=3)
        _,rows=await repair_counted_inventory(AsyncMock(return_value='not JSON'),'Read',[row],self.counts(),attempts=1)
        self.assertIs(rows[0],row)
        self.assertEqual(row.quantity_review['status'],'needs_review')

    def test_thickness_is_not_an_explicit_material_multiplier(self):
        from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
        for thickness in ('X1.5mm','X1,5mm','x 15 mm'):
            row=Device(category='ENCLOSURE',name='Vỏ tủ',spec='700x500x250 '+thickness,
                quantity=2,drawing_quantity=2,procurement_quantity=2,quantity_basis='Nhãn nguồn ghi 2 cái')
            AnalysisPipelineService._infer_practical_quantities([row])
            self.assertEqual(row.quantity,2)
        row=Device(category='MCB',name='MCB x4',spec='1P 10A',quantity=1)
        AnalysisPipelineService._infer_practical_quantities([row])
        self.assertEqual(row.quantity,4)

if __name__=='__main__':unittest.main()

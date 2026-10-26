import sys
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.inventory_validation import preserve_inventory_context, repair_counted_inventory


class InventoryContextTests(unittest.TestCase):
    def device(self, **kwargs):
        values = dict(category='MCCB', name='MCCB tổng', tag='QF1', spec='3P 200A 85kA', panel_code='TDT')
        return ExtractedDeviceSchema(**(values | kwargs))

    def test_preserves_prose_and_evidenced_accessory_but_not_old_crop(self):
        before = self.device(technical_analysis='Đóng cắt nguồn tổng.', notes='Nhận tín hiệu giám sát cháy',
            box_2d=[10, 10, 40, 40], evidence_image='old-image',
            accompanying_accessories=[{'name': 'Cơ cấu cắt từ xa', 'evidence': 'Dây tín hiệu đến MCCB'}])
        after = self.device()
        preserve_inventory_context([before], [after])
        self.assertEqual(after.technical_analysis, before.technical_analysis)
        self.assertEqual(after.notes, before.notes)
        self.assertEqual(after.accompanying_accessories, before.accompanying_accessories)
        self.assertIsNot(after.accompanying_accessories, before.accompanying_accessories)
        self.assertIsNone(after.box_2d)
        self.assertIsNone(after.evidence_image)

    def test_changed_rating_does_not_inherit_old_context(self):
        before = self.device(technical_analysis='Mô tả cũ')
        after = self.device(spec='3P 250A 85kA')
        preserve_inventory_context([before], [after])
        self.assertIsNone(after.technical_analysis)

    def test_repeated_tag_or_different_panel_cannot_borrow_context(self):
        before = self.device(technical_analysis='Mô tả cũ')
        after = self.device()
        preserve_inventory_context([before, self.device()], [after])
        self.assertIsNone(after.technical_analysis)
        preserve_inventory_context([before], [self.device(panel_code='OTHER')])

    def test_new_context_wins_and_unevidenced_accessories_are_not_restored(self):
        before = self.device(technical_analysis='Cũ', accompanying_accessories=[{'name': 'Phụ kiện suy đoán'}])
        after = self.device(technical_analysis='Mới')
        preserve_inventory_context([before], [after])
        self.assertEqual(after.technical_analysis, 'Mới')
        self.assertFalse(after.accompanying_accessories)


class RepairIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_count_repair_preserves_description_and_attached_source_equipment(self):
        before = ExtractedDeviceSchema(category='MCB', name='MCB', tag='QF1', spec='2P 30A 6kA',
            panel_code='TDT', quantity=1, technical_analysis='Bảo vệ nhánh.',
            accompanying_accessories=[{'name': 'Tiếp điểm phụ', 'evidence': 'Tiếp điểm nối về báo trạng thái'}])
        after = before.model_copy(deep=True)
        after.quantity = 2
        after.technical_analysis = None
        after.accompanying_accessories = []
        counts = {'counts': [{'panel_code': 'TDT', 'category': 'MCB', 'quantity': 2}]}
        with patch('app.services.ai.inventory_validation.extract_with_retry', AsyncMock(return_value=('response', [after]))):
            _, repaired = await repair_counted_inventory(AsyncMock(), 'Read source', [before], counts)
        self.assertEqual(repaired[0].quantity, 2)
        self.assertEqual(repaired[0].technical_analysis, before.technical_analysis)
        self.assertEqual(repaired[0].accompanying_accessories, before.accompanying_accessories)


if __name__ == '__main__':
    unittest.main()

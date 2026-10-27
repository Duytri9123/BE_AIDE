import tempfile
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
from app.services.ai.procurement_review import build_quotation_rows
from app.services.export.quotation_exporter import QuotationExporterService


class ReferenceLayoutTests(unittest.TestCase):
    def test_panels_and_sections_keep_every_device_and_accessory(self):
        devices = [dict(category='MCCB', name='Feeder', spec='3P160A', section='Đầu ra',
                        panel_code='MDB101', quantity=4),
                   dict(category='MCCB', name='Main', spec='3P630A', section='Đầu vào',
                        panel_code='MDB101', quantity=1,
                        accompanying_accessories=[dict(name='Cuộn cắt', quantity=1, evidence='Nguồn ghi')]),
                   dict(category='CT', name='CT', spec='600/5A', section='Đầu vào',
                        panel_code='MDB102', quantity=3)]
        with patch('app.services.ai.procurement_review.assembly_requirements', return_value=[]):
            rows = build_quotation_rows(devices, {}, refresh_prices=False)
        self.assertEqual([r['name'] for r in rows if r['row_type'] == 'section_header'],
                         ['Vỏ tủ + phụ kiện', 'Đầu vào', 'Đầu ra', 'Vỏ tủ + phụ kiện', 'Đầu vào'])
        self.assertEqual([r['quantity'] for r in rows if r['row_type'] == 'item'], [1, 4, 3])
        accessory = next(r for r in rows if r['row_type'] == 'accessory')
        parent = rows[rows.index(accessory) - 1]
        self.assertEqual(accessory['parent_id'], parent['id'])
        self.assertEqual([r['tt'] for r in rows if r['row_type'] == 'panel_header'], ['1', '2'])
        self.assertTrue(all(r['unit_price'] is None for r in rows if r['row_type'] == 'item'))

    def test_export_nine_visible_columns_and_formula_inputs_preserved(self):
        rows = [dict(row_type='panel_header', name='MDB101', quantity=1),
                dict(row_type='section_header', name='Đầu vào'),
                dict(row_type='item', name='MCCB', quantity=1, unit_price=100, origin='CHINT')]
        with tempfile.TemporaryDirectory() as folder, patch('app.services.export.quotation_exporter.settings.EXPORT_DIR', folder):
            book = load_workbook(QuotationExporterService.export(rows, proposals=[]))
            sheet = book.active
            self.assertEqual(sheet['B2'].value, 'TỦ ĐIỆN MDB101')
            self.assertEqual(sheet['B3'].value, 'Đầu vào')
            self.assertEqual(sheet['G4'].value, '=J4*(1-K4/100)')
            self.assertEqual(sheet['J4'].value, 100)
            self.assertTrue(sheet.column_dimensions['J'].hidden)
            self.assertTrue(sheet.column_dimensions['K'].hidden)
            self.assertIn('$A$1:$I$', str(sheet.print_area))
            book.close()


if __name__ == '__main__':
    unittest.main()

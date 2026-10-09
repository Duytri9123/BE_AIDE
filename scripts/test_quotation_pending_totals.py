import tempfile
import unittest
from unittest.mock import patch
from openpyxl import load_workbook
from app.services.export.quotation_exporter import QuotationExporterService


class PendingTotalsTests(unittest.TestCase):
    def export_rows(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            with patch('app.services.export.quotation_exporter.settings.EXPORT_DIR', directory):
                path = QuotationExporterService.export(rows, proposals=[])
                workbook = load_workbook(path)
                values = list(workbook.active.values)
                workbook.close()
                return values

    def test_missing_price_blocks_panel_and_all_totals(self):
        rows = self.export_rows([
            {'row_type': 'panel_header', 'name': 'Panel'},
            {'row_type': 'item', 'name': 'Known', 'quantity': 1, 'unit_price': 100},
            {'row_type': 'item', 'name': 'Pending', 'quantity': 1, 'unit_price': None},
        ])
        self.assertEqual(rows[1][6:8], ('Chưa đủ dữ liệu', 'Chưa đủ dữ liệu'))
        self.assertEqual([row[7] for row in rows[-3:]], ['Chưa đủ dữ liệu'] * 3)

    def test_confirmed_zero_price_still_has_numeric_formulas(self):
        rows = self.export_rows([
            {'row_type': 'panel_header', 'name': 'Panel'},
            {'row_type': 'item', 'name': 'Free', 'quantity': 1, 'unit_price': 0},
        ])
        self.assertEqual(rows[2][9], 0)
        self.assertTrue(rows[1][7].startswith('='))
        self.assertTrue(rows[-1][7].startswith('='))

    def test_unknown_quantity_is_pending_even_with_a_price(self):
        rows = self.export_rows([
            {'row_type': 'panel_header', 'name': 'Panel'},
            {'row_type': 'item', 'name': 'Unknown quantity', 'quantity': None, 'unit_price': 100},
        ])
        self.assertEqual(rows[1][7], 'Chưa đủ dữ liệu')


if __name__ == '__main__':
    unittest.main()

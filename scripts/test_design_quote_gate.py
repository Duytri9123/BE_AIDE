import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from app.api.v1.endpoints.export import export_excel_quotation, ExcelExportPayload, export_quotation
from app.schemas.export import ExportRequest
from app.services.cad.output_status import output_status

class DesignQuoteGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_legacy_export_cannot_bypass_incomplete_design(self):
        first = Mock()
        first.scalar_one_or_none.return_value = SimpleNamespace(id=16, user_id=1, name='Test')
        latest = Mock()
        latest.scalars.return_value.first.return_value = SimpleNamespace(confidence_scores={'design_result': {'cad_status': 'needs_review'}})
        db = SimpleNamespace(execute=AsyncMock(side_effect=[first, latest]))
        with patch('app.api.v1.endpoints.export.QuotationExporterService.export') as exporter:
            with self.assertRaises(HTTPException) as caught:
                await export_quotation(ExportRequest(project_id='16'), db, SimpleNamespace(id=1))
            self.assertEqual(caught.exception.status_code, 409)
            exporter.assert_not_called()

    async def test_client_rows_cannot_bypass_incomplete_design(self):
        project = SimpleNamespace(id=16, user_id=1, name='Test')
        first = Mock()
        first.scalar_one_or_none.return_value = project
        latest = Mock()
        latest.scalars.return_value.first.return_value = SimpleNamespace(confidence_scores={'design_result': {'cad_status': 'needs_review'}})
        db = SimpleNamespace(execute=AsyncMock(side_effect=[first, latest]))
        with patch('app.api.v1.endpoints.export.QuotationExporterService.export') as exporter:
            with self.assertRaises(HTTPException) as caught:
                await export_excel_quotation(ExcelExportPayload(project_id=16, devices=[{'name':'Injected row'}]), db, SimpleNamespace(id=1))
            self.assertEqual(caught.exception.status_code, 409)
            exporter.assert_not_called()

    def test_completed_design_does_not_require_an_excel_file(self):
        layout = {'placements':[{'tag':'Q1'}], 'release_ready':True,
                  'source_reconciliation': {'release_ready':True}}
        self.assertEqual(output_status(object(), None, layout, devices=[{'tag':'Q1'}])['cad_status'], 'ready')

if __name__ == '__main__':
    unittest.main()

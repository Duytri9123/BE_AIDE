import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from app.api.v1.endpoints.export import export_excel_quotation, ExcelExportPayload, export_quotation
from app.schemas.export import ExportRequest
from app.services.cad.output_status import output_status

class DesignQuoteGateTests(unittest.IsolatedAsyncioTestCase):
    def test_quotation_design_does_not_replace_source_extraction(self):
        from app.services.ai.analysis_result import _build_analysis_result_schema
        source = {'category':'CONTACTOR','name':'Source P2','spec':'2P 16A','quantity':1}
        revised = {**source, 'spec':'2P 20A', 'quantity':2}
        from uuid import uuid4
        result = _build_analysis_result_schema(uuid4(), 1, [source],
            {'source_configuration':'quotation','design_devices':[revised]},
            enclosure_spec={'incomer_rating':20})
        self.assertEqual(result.devices[0].spec, '2P 16A')
        self.assertEqual(result.devices[0].quantity, 1)

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

    async def test_takeoff_quotation_can_export_before_design(self):
        project = SimpleNamespace(id=16, user_id=1, name='Test')
        first = Mock()
        first.scalar_one_or_none.return_value = project
        latest = Mock()
        latest.scalars.return_value.first.return_value = SimpleNamespace(confidence_scores={'design_result': {'cad_status': 'needs_review'}})
        db = SimpleNamespace(execute=AsyncMock(side_effect=[first, latest]))
        with tempfile.TemporaryDirectory() as folder, patch('app.services.export.quotation_exporter.settings.EXPORT_DIR',folder):
            response=await export_excel_quotation(ExcelExportPayload(project_id=16,
                devices=[{'row_type':'item','name':'MCCB','quantity':1,'unit_price':None}]),db,SimpleNamespace(id=1))
            self.assertTrue(Path(response.path).is_file())

    def test_completed_design_does_not_require_an_excel_file(self):
        layout = {'placements':[{'tag':'Q1'}], 'release_ready':True,
                  'source_reconciliation': {'release_ready':True}}
        self.assertEqual(output_status(object(), None, layout, devices=[{'tag':'Q1'}])['cad_status'], 'ready')

if __name__ == '__main__':
    unittest.main()

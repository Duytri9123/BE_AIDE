import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from PIL import Image
import ezdxf
from app.services.ingestion.document_context import DocumentContextService

from app.services.ai.circuit_preflight import CircuitPreflightService


class CircuitPreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_images_are_assessed_before_takeoff(self):
        with tempfile.TemporaryDirectory() as folder:
            files = []
            for number in range(2):
                path = Path(folder) / f"sheet-{number + 1}.png"
                Image.new('RGB', (200, 100), 'white').save(path)
                files.append(SimpleNamespace(filename=path.name, file_path=str(path)))
            response = '{"circuit_summary":"Đã đọc cả hai trang", "file_roles":[], "circuits":[], "functional_groups":[], "ambiguous_symbols":[], "installation_considerations":[], "questions":[], "source_limits":[]}'
            with patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback',
                       new_callable=AsyncMock, return_value=(response, None)) as call:
                result = await CircuitPreflightService.assess(files, [], object(), [object()])
            self.assertEqual(result['status'], 'assessed')
            self.assertEqual(len(CircuitPreflightService._visual_pages(files)), 2)
            self.assertEqual(call.call_count, 1)

    def test_dxf_context_preserves_positions_and_blocks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'circuit.dxf'
            drawing = ezdxf.new()
            model = drawing.modelspace()
            model.add_text('SOURCE', dxfattribs={'insert': (10, 90)})
            model.add_text('LOAD', dxfattribs={'insert': (10, 10)})
            drawing.blocks.new('CONTACTOR')
            model.add_blockref('CONTACTOR', (10, 50))
            drawing.saveas(path)
            context = DocumentContextService._read_dxf_labels(path)
        self.assertLess(context.index('SOURCE'), context.index('CONTACTOR'))
        self.assertLess(context.index('CONTACTOR'), context.index('LOAD'))
        self.assertIn('Y=50', context)

    async def test_unreadable_document_cannot_pass_assessment(self):
        result = await CircuitPreflightService.assess([], [], object(), [object()])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(CircuitPreflightService.extraction_context(result), '')


if __name__ == '__main__':
    unittest.main()

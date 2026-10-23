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
    async def test_visual_malformed_response_retries_with_new_prompt(self):
        response = '{"circuit_summary":"Nguồn và tải", "has_sld":true}'
        call = AsyncMock(side_effect=[('invalid JSON', None), (response, None)])
        with patch.object(CircuitPreflightService, '_visual_pages', return_value=[('page.png', Image.new('RGB', (20, 20)))]), patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback', call):
            result = await CircuitPreflightService.assess([], [], object(), [object()])
        self.assertEqual(result['status'], 'assessed')
        self.assertNotEqual(call.call_args_list[0].kwargs['prompt'], call.call_args_list[1].kwargs['prompt'])

    async def test_one_failed_page_prevents_whole_document_approval(self):
        response = '{"circuit_summary":"Nguồn và tải", "has_sld":true}'
        call = AsyncMock(side_effect=[(response, None), ('invalid', None), ('invalid', None)])
        with patch.object(CircuitPreflightService, '_visual_pages', return_value=[('page1.png', Image.new('RGB', (20, 20))), ('page2.png', Image.new('RGB', (20, 20)))]), patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback', call):
            result = await CircuitPreflightService.assess([], [], object(), [object()])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(CircuitPreflightService.extraction_context(result), '')

    async def test_all_images_are_assessed_before_takeoff(self):
        with tempfile.TemporaryDirectory() as folder:
            files = []
            for number in range(2):
                path = Path(folder) / f"sheet-{number + 1}.png"
                Image.new('RGB', (200, 100), 'white').save(path)
                files.append(SimpleNamespace(filename=path.name, file_path=str(path)))
            response = '{"circuit_summary":"Đã đọc cả hai trang", "has_sld": true, "file_roles":[], "circuits":[], "functional_groups":[], "ambiguous_symbols":[], "installation_considerations":[], "questions":[], "source_limits":[]}'
            with patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback',
                       new_callable=AsyncMock, return_value=(response, None)) as call:
                result = await CircuitPreflightService.assess(files, [], object(), [object()])
            self.assertEqual(result['status'], 'assessed')
            self.assertEqual(len(CircuitPreflightService._visual_pages(files)), 2)
            self.assertEqual(call.call_count, 2)
            self.assertNotEqual(call.call_args_list[0].kwargs['image_path'],
                                call.call_args_list[1].kwargs['image_path'])

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

    async def test_reference_only_document_does_not_pass_as_sld(self):
        response = '{"circuit_summary":"Only a price list", "has_sld": false}'
        contexts = [{'filename': 'prices.txt', 'text': 'price list'}]
        with patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback',
                   new_callable=AsyncMock, return_value=(response, None)):
            result = await CircuitPreflightService.assess([], contexts, object(), [object()])
        self.assertEqual(result['status'], 'unavailable')

    async def test_unreadable_document_cannot_pass_assessment(self):
        result = await CircuitPreflightService.assess([], [], object(), [object()])
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(CircuitPreflightService.extraction_context(result), '')

    async def test_pipeline_progress_callback_is_accepted(self):
        events = []
        result = await CircuitPreflightService.assess(
            [], [], object(), [object()], progress_callback=events.append
        )
        self.assertEqual(result['status'], 'unavailable')


if __name__ == '__main__':
    unittest.main()

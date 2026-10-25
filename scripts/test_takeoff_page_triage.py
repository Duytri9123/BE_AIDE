import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from PIL import Image
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService

class PageTriageTests(unittest.IsolatedAsyncioTestCase):
    async def triage(self, answers, total=1):
        page = SimpleNamespace(render=lambda **kw: SimpleNamespace(to_pil=lambda: Image.new('RGB', (20, 20))))
        ai = SimpleNamespace(provider='test', api_key='test', selected_model='test')
        call = AsyncMock(side_effect=answers)
        with patch('app.services.ai.analysis_pipeline_service.VisionAnalyzerService.analyze_image', call):
            result = await AnalysisPipelineService._preflight_pdf_with_vision(
                [page] * total, total, ai, user_requirement='Chỉ tủ TĐT')
        return result, call

    async def test_requirement_is_in_page_selection(self):
        result, call = await self.triage(['{"relevant_pages":[1]}'])
        self.assertEqual(result, [1])
        self.assertIn('Chỉ tủ TĐT', call.call_args.kwargs['prompt'])

    async def test_one_failed_batch_does_not_silently_drop_pages(self):
        result, _ = await self.triage(['{"relevant_pages":[1]}', 'invalid'], total=13)
        self.assertIsNone(result)

    async def test_malformed_page_list_requires_retry(self):
        result, _ = await self.triage(['{"relevant_pages":"all"}'])
        self.assertIsNone(result)

    async def test_invalid_page_ids_are_rejected(self):
        for value in ('true', '1.5', '99', '0', '"outside"'):
            with self.subTest(value=value):
                result, _ = await self.triage(['{"relevant_pages":[' + value + ']}'])
                self.assertIsNone(result)

    async def test_empty_selection_stays_empty(self):
        result, _ = await self.triage(['{"relevant_pages":[]}'])
        self.assertEqual(result, [])


class ScopedPdfTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_requested_pdf_page_is_reviewed_with_its_text(self):
        import tempfile
        from pathlib import Path
        from app.services.ai.circuit_preflight import CircuitPreflightService
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'drawing.pdf'
            # A real two-page PDF with independent text streams; no extra PDF writer dependency.
            objects = [
                b'<< /Type /Catalog /Pages 2 0 R >>',
                b'<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 7 0 R >> >> /Contents 5 0 R >>',
                b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>',
            ]
            for text in ('EXCLUDED_PAGE_ONE', 'SELECTED_PAGE_TWO'):
                stream = f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode()
                objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
            objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
            pdf = b'%PDF-1.4\n'
            offsets = [0]
            for number, obj in enumerate(objects, 1):
                offsets.append(len(pdf))
                pdf += f'{number} 0 obj\n'.encode() + obj + b'\nendobj\n'
            xref = len(pdf)
            pdf += f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
            pdf += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
            pdf += f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
            path.write_bytes(pdf)
            file = SimpleNamespace(filename='drawing.pdf', file_path=str(path))
            call = AsyncMock(return_value=('{"circuit_summary":"Selected circuit", "has_sld":true}', None))
            with patch('app.services.ai.circuit_preflight.ConnectionPoolService.call_with_fallback', call), patch.object(AnalysisPipelineService, '_preflight_pdf_with_vision', new_callable=AsyncMock) as triage:
                result = await CircuitPreflightService.assess(
                    [file], [{'filename':'drawing.pdf', 'text':'EXCLUDED_PAGE_ONE SELECTED_PAGE_TWO'}],
                    object(), [object()], user_prompt='trang 2')
            triage.assert_not_awaited()
            self.assertEqual(call.await_count, 1)
            prompt = call.call_args.kwargs['prompt']
            self.assertIn('SELECTED_PAGE_TWO', prompt)
            self.assertNotIn('EXCLUDED_PAGE_ONE', prompt)
            self.assertEqual(result['selected_pdf_pages'][str(path)], [2])
            self.assertEqual(result['status'], 'assessed')

if __name__ == '__main__':
    unittest.main()

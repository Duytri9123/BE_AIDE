import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from app.api.v1.endpoints.cad_library import manifest, resolve_model_asset
from app.api.v1.endpoints.devices import get_device_views
from app.services.cad.library_taxonomy import classify, explicit_brands


class CadLinkTests(unittest.TestCase):
    def test_cad_generation_uses_source_without_inventing_side(self):
        import ezdxf
        from app.services.cad.enclosure_cad_generator import EnclosureCadGeneratorService
        asset = next(i for i in manifest()['items'] if i['name'] == 'Den DO')
        doc = ezdxf.new()
        device = {'cad': {'asset_id': asset['id']}}
        size = EnclosureCadGeneratorService._insert_device(doc.modelspace(), device, 50, 80)
        self.assertGreater(size[0], 0)
        self.assertEqual(len(doc.modelspace()), 1)
        self.assertEqual(EnclosureCadGeneratorService._insert_device(doc.modelspace(), device, 0, 0, side=True), (0, 0))
        self.assertEqual(len(doc.modelspace()), 1)
        self.assertFalse(doc.audit().errors)

    def test_devices_accessories_and_explicit_brands(self):
        self.assertEqual(classify('Quạt trên nóc')['kind'], 'accessory')
        self.assertEqual(classify('Nút nhấn')['kind'], 'device')
        self.assertEqual(classify('*U123', 'Đèn báo pha')['group'], 'Đèn báo')
        self.assertEqual(classify('anonymous')['kind'], 'unclassified')
        self.assertEqual(explicit_brands('Đèn báo Idec'), ['Idec'])
        self.assertEqual(explicit_brands('Den DO'), [])
    def test_legacy_sku_resolves_without_seed_metadata(self):
        asset = next(i for i in manifest()['items'] if i['name'] == 'Den DO')
        self.assertEqual(resolve_model_asset('CAD:' + asset['id'], {})['id'], asset['id'])
        self.assertIsNone(resolve_model_asset('no-match', {'cad': {'asset_id': 'missing'}}))

    def test_legacy_preview_returns_geometry_not_empty_envelopes(self):
        asset = next(i for i in manifest()['items'] if i['name'] == 'Den DO')
        model = SimpleNamespace(sku='CAD:' + asset['id'], parameters={}, dimensions={})
        class Session:
            async def get(self, *_): return model
        result = asyncio.run(get_device_views(1, Session()))
        self.assertEqual(result['source'], 'cad_library')
        self.assertIn('<svg', result['views'][0]['svg'])
        self.assertGreater(len(result['views'][0]['svg']), 1000)

    def test_missing_cad_does_not_silently_become_a_box(self):
        model = SimpleNamespace(sku='CAD:missing', parameters={}, dimensions={'w': 10, 'h': 20})
        class Session:
            async def get(self, *_): return model
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(get_device_views(1, Session()))
        self.assertEqual(caught.exception.status_code, 404)

    def test_source_cells_cover_loose_geometry_categories(self):
        cells = [i for i in manifest()['items'] if i['library'] == 'source_cells']
        names = {i['name'] for i in cells}
        self.assertTrue({'Quạt', 'Nút nhấn', 'Đèn báo pha', 'Tấm lọc', 'Cầu chì'} <= names)
        self.assertTrue(any('TỔNG HỢP 1.bak' in i['source_files'] for i in cells))


if __name__ == '__main__':
    unittest.main()

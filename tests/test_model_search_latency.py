"""Model-only lookups must not enumerate the CAD library."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.v1.endpoints.devices import get_models
from app.api.v1.endpoints import cad_library


class ModelSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_search_without_cad_links_skips_manifest(self):
        model = SimpleNamespace(id=1, parameters={'cad': {'catalog_id': 'linked-model'}}, dimensions={}, series=None,
                                sku='MCB-TEST', name='MCB test', price=100, discount_pct=0,
                                device_series_id=1)
        result = MagicMock()
        result.scalars.return_value.all.return_value = [model]
        db = SimpleNamespace(execute=AsyncMock(return_value=result))
        with patch.object(cad_library, 'manifest', side_effect=AssertionError('Unexpected CAD scan')), \
             patch.object(cad_library, 'resolve_model_asset', side_effect=AssertionError('Unexpected CAD resolution')):
            rows = await get_models(q='MCB', db=db)
        self.assertEqual([row.sku for row in rows], ['MCB-TEST'])
        self.assertIsNone(rows[0].parameters['cad'])

    def test_unlinked_model_resolution_skips_manifest(self):
        with patch.object(cad_library, 'manifest', side_effect=AssertionError('Unexpected CAD scan')):
            self.assertIsNone(cad_library.resolve_model_asset('MCB', {}))

    def test_linked_model_still_resolves_exact_catalog_asset(self):
        asset = {'catalog_id': 'exact', 'filename': 'model.dxf'}
        with patch.object(cad_library, 'manifest', return_value={'items': [asset]}) as manifest, \
             patch('pathlib.Path.is_file', return_value=True):
            self.assertIs(cad_library.resolve_model_asset('MCB', {'cad': {'catalog_id': 'exact'}}), asset)
            manifest.assert_called_once()


class TextOnlyToolTests(unittest.TestCase):
    def test_text_requests_cannot_search_cad(self):
        from app.services.ai.el_tools import permits_tool
        tools = [
            {'path': '/api/v1/cad-library', 'writes': False},
            {'path': '/api/v1/equipment-library', 'writes': False},
            {'path': '/api/v1/devices/browse', 'writes': False},
            {'kind': 'cad', 'name': 'cad_get_models', 'writes': False},
        ]
        for message in ['Tra mã MCB LS và thông số', 'Chỉ text, không thiết kế', 'Báo giá thiết bị']:
            for tool in tools:
                with self.subTest(message=message, tool=tool):
                    self.assertFalse(permits_tool(tool, message))

    def test_text_catalog_and_design_cad_remain_available(self):
        from app.services.ai.el_tools import permits_tool
        self.assertTrue(permits_tool({'path': '/api/v1/devices/models', 'writes': False}, 'Tra mã MCB LS'))
        self.assertTrue(permits_tool({'path': '/api/v1/device-catalog', 'writes': False}, 'Tra giá MCB LS'))
        self.assertTrue(permits_tool({'path': '/api/v1/cad-library', 'writes': False}, 'Thiết kế tủ điện'))
        self.assertFalse(permits_tool({'path': '/api/v1/cad-library', 'writes': False}, 'Không thiết kế, chỉ tra mã'))

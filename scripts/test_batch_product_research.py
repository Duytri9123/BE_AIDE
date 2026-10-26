"""Whole-table research: preserve internal choices and validate group/source identity."""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai import web_device_recommendations as research
from app.services.ai.takeoff_scope import complete_accessories


class BatchResearchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        research._RESEARCH_CACHE.clear()
        self.connection = SimpleNamespace(provider='google', api_key='test', selected_model='test', quotas={})

    def device(self, poles=2, current=30, **kwargs):
        return ExtractedDeviceSchema(category='MCB', name='MCB', spec=f'{poles}P {current}A 6kA',
                                     poles=poles, in_a=current, icu_ka=6, **kwargs)

    def response(self):
        rows = []
        sources = []
        for index, (poles, current, sku) in enumerate([(2, 30, 'A9F74230'), (3, 20, 'A9F74320')]):
            sources.append({'title': f'Schneider Electric MCB {sku} {poles}P {current}A 6kA',
                            'url': f'https://www.se.com/product/{sku}/', 'snippet': sku})
            rows.append({'id': f'g{index}', 'candidates': [{'brand': 'Schneider Electric', 'sku': sku,
                'name': f'MCB {sku}', 'source_id': index, 'function_match': True, 'voltage_match': True,
                'technical_evidence': f'{poles}P {current}A 6kA',
                'parameters': {'poles': poles, 'in_a': current, 'icu_ka': 6}}]})
        return {'success': True, 'results': sources, 'answer': json.dumps({'devices': rows})}

    async def test_one_search_maps_groups_and_reuses_duplicate_rows(self):
        devices = [self.device(), self.device(), self.device(3, 20)]
        events = []
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=self.response())) as search:
            await research.research_device_products(devices, [self.connection], progress_callback=events.append)
        self.assertEqual(search.await_count, 1)
        self.assertEqual(len(events), 2)
        self.assertEqual(devices[0].catalog_candidates, devices[1].catalog_candidates)
        self.assertIsNot(devices[0].catalog_candidates, devices[1].catalog_candidates)
        self.assertEqual(devices[0].catalog_candidates['Schneider Electric'][0]['sku'], 'A9F74230')
        self.assertEqual(devices[2].catalog_candidates['Schneider Electric'][0]['sku'], 'A9F74320')
        self.assertTrue(all(d.web_research['status'] == 'products_found' for d in devices))

    async def test_internal_products_need_no_web(self):
        device = self.device(catalog_candidates={'LS Electric': [{'sku': 'BKN', 'auto_selectable': True}]})
        with patch.object(research.WebSearchService, 'search', AsyncMock()) as search:
            await research.research_device_products([device], [self.connection])
        search.assert_not_awaited()
        self.assertEqual(device.catalog_candidates['LS Electric'][0]['sku'], 'BKN')
        self.assertEqual(device.web_research['status'], 'internal_catalog')

    async def test_internal_lookup_keeps_requested_brand(self):
        device = self.device(catalog_candidates={'LS Electric': [{'sku': 'BKN', 'auto_selectable': True}]})
        await research.research_device_products([device], [], preferred_brand='LS Electric')
        self.assertEqual(device.web_research['requested_brand'], 'LS Electric')

    async def test_internal_placeholder_without_sku_does_not_skip_research(self):
        device = self.device(catalog_matches={'LS Electric': {'meets_icu': True}})
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=self.response())) as search:
            await research.research_device_products([device], [self.connection])
        self.assertEqual(search.await_count, 1)
        self.assertTrue(device.catalog_candidates)

    async def test_failed_search_preserves_internal_references(self):
        choices = {'LS Electric': [{'sku': 'review-only', 'rating_complete': False}]}
        device = self.device(catalog_candidates=choices)
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value={'success': False})):
            await research.research_device_products([device], [self.connection])
        self.assertEqual(device.catalog_candidates, choices)
        self.assertEqual(device.web_research['status'], 'search_unavailable')

    async def test_web_results_merge_without_replacing_internal_rows(self):
        device = self.device(catalog_candidates={'LS Electric': [{'sku': 'reference'}]})
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=self.response())):
            await research.research_device_products([device], [self.connection])
        self.assertIn('LS Electric', device.catalog_candidates)
        self.assertIn('Schneider Electric', device.catalog_candidates)

    async def test_cached_results_do_not_search_again(self):
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=self.response())) as search:
            await research.research_device_products([self.device()], [self.connection])
            device = self.device()
            await research.research_device_products([device], [self.connection])
        self.assertEqual(search.await_count, 1)
        self.assertTrue(device.web_research['cache_hit'])

    async def test_wrong_group_ratings_are_not_applied(self):
        response = self.response()
        payload = json.loads(response['answer'])
        payload['devices'][0]['candidates'] = payload['devices'][1]['candidates']
        response['answer'] = json.dumps(payload)
        device = self.device()
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=response)), \
             patch.object(research.VisionAnalyzerService, 'analyze_text', AsyncMock(return_value=response['answer'])):
            await research.research_device_products([device], [self.connection])
        self.assertFalse(device.catalog_candidates)

    async def test_parses_all_search_excerpts_in_one_model_call(self):
        response = self.response()
        answer = response['answer']
        response['answer'] = 'See cited manufacturer excerpts.'
        devices = [self.device(), self.device(3, 20)]
        with patch.object(research.WebSearchService, 'search', AsyncMock(return_value=response)) as search, \
             patch.object(research.VisionAnalyzerService, 'analyze_text', AsyncMock(return_value=answer)) as parser:
            await research.research_device_products(devices, [self.connection])
        self.assertEqual(search.await_count, 1)
        self.assertEqual(parser.await_count, 1)
        self.assertTrue(all(d.catalog_candidates for d in devices))

    async def test_parent_and_accessories_share_one_research_batch(self):
        devices = [self.device(accompanying_accessories=[{'category': 'AUX_CONTACT', 'name': 'Tiếp điểm phụ'}]),
                   self.device(3, 20, accompanying_accessories=[{'category': 'SHUNT_TRIP', 'name': 'Cuộn cắt'}])]
        with patch('app.services.ai.web_device_recommendations.research_device_products', AsyncMock()) as lookup, \
             patch('app.services.ai.takeoff_pricebook.link_devices', Mock()):
            await complete_accessories(devices, '', [], None, include_devices=True)
        self.assertEqual(lookup.await_count, 1)
        self.assertEqual(len(lookup.call_args.args[0]), 4)
        self.assertTrue(devices[1].accompanying_accessories[0]['compatibility_status'])


if __name__ == '__main__':
    unittest.main()

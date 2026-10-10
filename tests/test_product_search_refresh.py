import unittest
from unittest.mock import AsyncMock, patch
from app.services.ai.web_search_service import WebSearchService


class SearchRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_bypasses_cached_product(self):
        with patch('app.services.ai.web_search_service.cache_service.get', new_callable=AsyncMock) as cache_get, \
             patch('app.services.ai.web_search_service.cache_service.set', new_callable=AsyncMock), \
             patch.object(WebSearchService, '_search_tavily', new_callable=AsyncMock) as provider:
            provider.return_value = {'success': True, 'results': [], 'answer': 'new'}
            result = await WebSearchService.search('Chint model 20A', 'tavily', 'test', refresh=True)
            cache_get.assert_not_awaited()
            provider.assert_awaited_once()
            self.assertEqual(result['answer'], 'new')

    async def test_full_specification_separates_cache_keys(self):
        with patch('app.services.ai.web_search_service.cache_service.get', new_callable=AsyncMock) as cache_get, \
             patch('app.services.ai.web_search_service.cache_service.set', new_callable=AsyncMock), \
             patch.object(WebSearchService, '_search_tavily', new_callable=AsyncMock) as provider:
            cache_get.return_value = None
            provider.return_value = {'success': True, 'results': []}
            prefix = 'Chint official datasheet ' + 'same ' * 30
            await WebSearchService.search(prefix + '20A', 'tavily', 'test')
            await WebSearchService.search(prefix + '30A', 'tavily', 'test')
            self.assertNotEqual(cache_get.await_args_list[0].args[0], cache_get.await_args_list[1].args[0])

import unittest
from unittest.mock import AsyncMock, patch
from app.services.ai.web_search_service import WebSearchService


class WebSearchCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_structured_search_result_uses_json_cache(self):
        result = {'success': True, 'answer': 'verified reference', 'results': []}
        with patch('app.services.ai.web_search_service.cache_service') as cache, \
             patch.object(WebSearchService, '_search_tavily', new_callable=AsyncMock, return_value=result) as provider:
            cache.get_json = AsyncMock(side_effect=[None, result])
            cache.set_json = AsyncMock(return_value=True)
            first = await WebSearchService.search('reference', 'tavily', 'test-key')
            second = await WebSearchService.search('reference', 'tavily', 'test-key')
            self.assertEqual(first, second)
            provider.assert_awaited_once()
            cache.set_json.assert_awaited_once()
            self.assertEqual(cache.set_json.call_args.kwargs['expire'], 86400)
            cache.set.assert_not_called()

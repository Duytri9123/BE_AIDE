import unittest
from unittest.mock import Mock, AsyncMock, patch
from redis.exceptions import TimeoutError
from app.services.ai.progress_delivery import deliver


class ProgressDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_transport_retries_same_event(self):
        callback=Mock(side_effect=[TimeoutError('transport'),None])
        with patch('app.services.ai.progress_delivery.asyncio.sleep',new_callable=AsyncMock):
            await deliver(callback,{'stage':'normalize'})
        self.assertEqual(callback.call_count,2)
        self.assertEqual(callback.call_args_list[0],callback.call_args_list[1])

    async def test_cancel_is_not_retried(self):
        callback=Mock(side_effect=ValueError('cancelled'))
        with self.assertRaises(ValueError):await deliver(callback,{})
        self.assertEqual(callback.call_count,1)

    async def test_persistent_transport_error_is_not_hidden(self):
        callback=Mock(side_effect=TimeoutError('transport'))
        with patch('app.services.ai.progress_delivery.asyncio.sleep',new_callable=AsyncMock):
            with self.assertRaises(TimeoutError):await deliver(callback,{})
        self.assertEqual(callback.call_count,3)

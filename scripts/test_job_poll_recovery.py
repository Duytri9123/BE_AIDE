import json
import unittest
from unittest.mock import AsyncMock, patch

import redis
from fastapi import HTTPException
from app.services.job_queue import wait_result


class JobPollRecovery(unittest.IsolatedAsyncioTestCase):
    async def test_transient_timeout_preserves_accepted_job_result(self):
        client = AsyncMock()
        client.hgetall.side_effect = [redis.TimeoutError('temporary'),
            {'status': 'SUCCESS', 'result': json.dumps({'devices': [1]})}]
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch('app.services.job_queue.async_redis.from_url', return_value=manager), \
             patch('app.services.job_queue.asyncio.sleep', new_callable=AsyncMock):
            self.assertEqual(await wait_result('accepted'), {'devices': [1]})
        self.assertEqual(client.hgetall.call_count, 2)

    async def test_terminal_failure_still_reports_source_error(self):
        client = AsyncMock()
        client.hgetall.return_value = {'status': 'FAILURE', 'message': 'Source unreadable'}
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch('app.services.job_queue.async_redis.from_url', return_value=manager):
            with self.assertRaises(HTTPException) as error:
                await wait_result('accepted')
        self.assertEqual(error.exception.status_code, 422)
        self.assertEqual(error.exception.detail, 'Source unreadable')


if __name__ == '__main__':
    unittest.main()

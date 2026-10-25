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

    async def test_long_running_job_has_no_thirty_minute_poll_deadline(self):
        client = AsyncMock()
        client.hgetall.side_effect = [{'status': 'PROGRESS'}] * 1801 + [
            {'status': 'SUCCESS', 'result': json.dumps({'devices': [2]})}]
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch('app.services.job_queue.async_redis.from_url', return_value=manager), patch('app.services.job_queue.asyncio.sleep', new_callable=AsyncMock):
            self.assertEqual(await wait_result('long-job'), {'devices': [2]})
        self.assertEqual(client.hgetall.await_count, 1802)

    async def test_missing_job_does_not_wait_forever(self):
        client = AsyncMock()
        client.hgetall.return_value = {}
        manager = AsyncMock()
        manager.__aenter__.return_value = client
        with patch('app.services.job_queue.async_redis.from_url', return_value=manager):
            with self.assertRaises(HTTPException) as error:
                await wait_result('missing')
        self.assertEqual(error.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()

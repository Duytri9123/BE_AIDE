import json
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch
import redis
from app.services import catalogtb_display_cache as cache


class DisplayCacheTests(TestCase):
    def test_redis_roundtrip_and_expiry(self):
        client = Mock()
        client.setex.return_value = True
        with patch.object(cache, '_client', client), patch.object(cache, '_retry_after', 0):
            data = {'items': [{'id': 'one'}]}
            self.assertTrue(cache.write_snapshot(Path('.'), data))
            key, ttl, raw = client.setex.call_args.args
            self.assertEqual(ttl, 60)
            self.assertTrue(key.startswith('aide:catalogtb:display:v2:'))
            client.get.return_value = raw
            self.assertEqual(cache.read_snapshot(Path('.'))[0], data)
            payload = json.loads(raw)
            payload['expires_at'] = time.time() - 1
            client.get.return_value = json.dumps(payload)
            self.assertIsNone(cache.read_snapshot(Path('.')))

    def test_redis_failure_does_not_repeat_timeout_per_request(self):
        client = Mock()
        client.get.side_effect = redis.TimeoutError()
        with patch.object(cache, '_client', client), patch.object(cache, '_retry_after', 0):
            self.assertIsNone(cache.read_snapshot(Path('.')))
            self.assertIsNone(cache.read_snapshot(Path('.')))
            self.assertFalse(cache.write_snapshot(Path('.'), {'items': []}))
            client.get.assert_called_once()
            client.setex.assert_not_called()

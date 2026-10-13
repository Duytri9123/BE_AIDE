"""Local, isolated read API load test. Never calls AI or modifies source DB."""
import asyncio
import argparse
import collections
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tmp' / 'load_test_20261008'
BASE = 'http://127.0.0.1:18080'
PATHS = ['/api/v1/users/me', '/api/v1/projects?limit=20',
         '/api/v1/projects/stats', '/api/v1/device-library/brands',
         '/api/v1/device-library/categories']


def percentile(values, q):
    return round(sorted(values)[min(len(values)-1, int((len(values)-1)*q))], 1) if values else None


async def stage(client, users, seconds=20, think=1.0):
    latencies, success_latencies, errors = [], [], collections.Counter()
    endpoint = collections.defaultdict(lambda: {'count': 0, 'errors': 0, 'latencies': []})
    start = time.perf_counter()
    deadline = start + seconds
    async def user(i):
        await asyncio.sleep((i / users) * 2)
        n = i
        while time.perf_counter() < deadline:
            path = PATHS[n % len(PATHS)]
            t = time.perf_counter()
            ok = False
            try:
                r = await client.get(path)
                ok = r.status_code == 200
                if not ok:
                    errors[str(r.status_code)] += 1
            except Exception as exc:
                errors[type(exc).__name__] += 1
            ms = (time.perf_counter()-t)*1000
            latencies.append(ms)
            if ok:
                success_latencies.append(ms)
            item = endpoint[path]
            item['count'] += 1
            item['errors'] += int(not ok)
            item['latencies'].append(ms)
            n += 1
            await asyncio.sleep(think)
    await asyncio.gather(*(user(i) for i in range(users)))
    elapsed = time.perf_counter()-start
    result = {'users': users, 'active_window_seconds': seconds, 'elapsed_seconds': round(elapsed, 2),
              'think_seconds': think, 'requests': len(latencies), 'errors': dict(errors),
              'error_percent': round(100*sum(errors.values())/max(1,len(latencies)), 2),
              'rps_including_drain': round(len(latencies)/elapsed, 2),
              'p50_ms': percentile(latencies, .5), 'p95_ms': percentile(latencies,.95),
              'p99_ms': percentile(latencies,.99), 'success_p95_ms': percentile(success_latencies,.95),
              'endpoints': {p: {'count':v['count'],'errors':v['errors'],
                                'p95_ms':percentile(v['latencies'],.95)} for p,v in endpoint.items()}}
    print(json.dumps(result), flush=True)
    return result


async def run(levels, duration, think):
    OUT.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(ROOT / 'webbaogia.db')
    copy = sqlite3.connect(OUT / 'snapshot.db')
    source.backup(copy)
    uid = copy.execute("select id from users where status='active' order by id limit 1").fetchone()[0]
    source.close()
    copy.close()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from app.core.security import create_access_token
    token = create_access_token(uid)
    env = os.environ.copy()
    env['DATABASE_URL'] = 'sqlite+aiosqlite:///' + (OUT / 'snapshot.db').as_posix()
    env['DB_ECHO'] = 'false'
    results = []
    with (OUT / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                   '--host','127.0.0.1','--port','18080','--no-access-log'],
                                  cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            async with httpx.AsyncClient(base_url=BASE, timeout=15,
                    limits=httpx.Limits(max_connections=1600, max_keepalive_connections=1600),
                    headers={'Authorization':'Bearer '+token}, trust_env=False) as client:
                for _ in range(120):
                    if server.poll() is not None:
                        raise RuntimeError('Server exited; inspect server.log')
                    try:
                        if (await client.get('/health')).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError('Startup timeout')
                preflight = []
                for path in PATHS:
                    t = time.perf_counter()
                    response = await client.get(path)
                    preflight.append({'path':path,'status':response.status_code,'ms':round((time.perf_counter()-t)*1000,1)})
                    print('preflight',path,response.status_code,flush=True)
                    if response.status_code != 200:
                        raise RuntimeError('Preflight failed: '+path)
                (OUT / 'preflight.json').write_text(json.dumps(preflight,indent=2),encoding='utf-8')
                for users in levels:
                    results.append(await stage(client,users,duration,think))
                    (OUT / 'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
                    await asyncio.sleep(3)
                    if results[-1]['error_percent'] > 10:
                        print('Stopping escalation: errors exceed 10%',flush=True)
                        break
        finally:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--users', type=int, nargs='+', default=[10,100,300,1000,1500])
    parser.add_argument('--duration', type=int, default=20)
    parser.add_argument('--think', type=float, default=1.0)
    args = parser.parse_args()
    if min(args.users) < 1 or args.duration < 1 or args.think < 0:
        parser.error('Users/duration must be positive; think must be nonnegative')
    asyncio.run(run(args.users,args.duration,args.think))

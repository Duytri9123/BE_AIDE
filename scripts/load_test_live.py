"""Progressive read-only load test of the owner's deployed elquote API.

Stops escalation when p95 exceeds 5 seconds or errors exceed 2%.
No AI calls, account creation, database changes, or deployment changes.
"""
import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tmp' / 'live_load_20261008'
PATHS = ['/api/v1/users/me', '/api/v1/projects?limit=20', '/api/v1/projects/stats',
         '/api/v1/device-library/brands', '/api/v1/device-library/categories']


def pct(values, q):
    return round(sorted(values)[int((len(values)-1)*q)], 1) if values else None


async def stage(client, users, duration, think):
    start = time.perf_counter()
    end = start + duration
    records = []
    lag = []
    peak_inflight = inflight = 0
    async def monitor():
        while time.perf_counter() < end:
            t = time.perf_counter()
            await asyncio.sleep(.1)
            lag.append(max(0, (time.perf_counter()-t-.1)*1000))
    async def user(i):
        nonlocal peak_inflight, inflight
        await asyncio.sleep(i/users*min(5,duration/2))
        n = i
        while time.perf_counter() < end:
            path = PATHS[n % len(PATHS)]
            t = time.perf_counter()
            inflight += 1
            peak_inflight = max(peak_inflight, inflight)
            error, status = None, None
            try:
                r = await asyncio.wait_for(client.get(path), timeout=15)
                status = r.status_code
                if status != 200:
                    error = 'HTTP_'+str(status)
                elif 'application/json' not in r.headers.get('content-type',''):
                    error = 'UnexpectedContentType'
                else:
                    r.json()
            except Exception as e:
                error = type(e).__name__
            finally:
                inflight -= 1
            records.append({'path':path, 'status':status,'error':error,
                            'ms':round((time.perf_counter()-t)*1000,2)})
            n += 1
            await asyncio.sleep(think)
    await asyncio.gather(monitor(),*(user(i) for i in range(users)))
    elapsed = time.perf_counter()-start
    timings = [r['ms'] for r in records]
    errors = Counter(r['error'] for r in records if r['error'])
    groups = defaultdict(list)
    for record in records:
        groups[record['path']].append(record)
    result = {'users':users,'window_seconds':duration,'elapsed_seconds':round(elapsed,2),
              'think_seconds':think,'requests':len(records),'errors':dict(errors),
              'error_percent':round(100*sum(errors.values())/max(1,len(records)),2),
              'p50_ms':pct(timings,.5),'p95_ms':pct(timings,.95),'p99_ms':pct(timings,.99),
              'rps_including_drain':round(len(records)/elapsed,2),
              'peak_inflight':peak_inflight,'generator_lag_p95_ms':pct(lag,.95),
              'endpoints':{p:{'requests':len(rs),'errors':sum(bool(r['error']) for r in rs),
                            'p95_ms':pct([r['ms'] for r in rs],.95)} for p,rs in groups.items()}}
    (OUT / f'requests_{users}.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    return result


async def run(args):
    global OUT
    if args.output_dir:
        OUT = Path(args.output_dir).resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    os.chdir(ROOT)
    sys.path.insert(0,str(ROOT))
    from app.core.security import create_access_token
    with sqlite3.connect('file:'+str(ROOT/'webbaogia.db')+'?mode=ro',uri=True) as db:
        role_filter = "role = 'admin'" if args.identity_role == 'admin' else "role != 'admin'"
        uid = db.execute("SELECT id FROM users WHERE status='active' AND deleted_at IS NULL AND "+role_filter+" ORDER BY tokens DESC LIMIT 1").fetchone()[0]
    token = create_access_token(uid)
    summary = {'started_utc':datetime.now(timezone.utc).isoformat(),'base_url':args.base_url,
               'target_levels':args.users,'stages':[],'stop_reason':None,'identity_role':args.identity_role,
               'method':'closed-loop GET JSON APIs, shared test identity, client/server on same machine',
               'limits':{'p95_ms':5000,'error_percent':2,'request_deadline_seconds':15}}
    async with httpx.AsyncClient(base_url=args.base_url,timeout=15,follow_redirects=True,
            limits=httpx.Limits(max_connections=max(args.users),max_keepalive_connections=min(max(args.users),2000)),
            headers={'Authorization':'Bearer '+token,'User-Agent':'Elquote-Owner-LoadTest/1.0'},trust_env=False) as client:
        for path in PATHS:
            r = await client.get(path)
            print('preflight',path,r.status_code,r.headers.get('content-type'),flush=True)
            if r.status_code != 200 or 'application/json' not in r.headers.get('content-type',''):
                raise RuntimeError('Preflight failed; no escalation: '+path)
        for users in args.users:
            result = await stage(client,users,args.duration,args.think)
            summary['stages'].append(result)
            if result['error_percent'] > 2 or result['p95_ms'] > 5000:
                summary['stop_reason'] = f"Escalation stopped at {users}: p95={result['p95_ms']}ms, errors={result['error_percent']}%"
            (OUT/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            if summary['stop_reason']:
                print(summary['stop_reason'],flush=True)
                break
            await asyncio.sleep(5)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',default='https://www.elquote.top')
    p.add_argument('--users',type=int,nargs='+',default=[1,10,50,100,300,1000,3000,10000])
    p.add_argument('--duration',type=int,default=20)
    p.add_argument('--think',type=float,default=1)
    p.add_argument('--identity-role',choices=['user','admin'],default='user')
    p.add_argument('--output-dir')
    args = p.parse_args()
    if min(args.users)<1 or args.duration<1 or args.think<0:
        p.error('invalid users/duration/think')
    asyncio.run(run(args))

"""Read-only integration probe for LS MCB text tools against the local database."""
import asyncio
import json
import statistics
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from app.api.deps import get_current_active_user
from app.api.v1.endpoints import devices, device_catalog
from app.db.session import AsyncSessionLocal
from app.services.ai.el_tools import api_tools, execute_api_tool, permits_tool, requires_cad

async def main():
    app = FastAPI()
    app.include_router(devices.router, prefix='/api/v1/devices')
    app.include_router(device_catalog.router, prefix='/api/v1/device-catalog')
    app.dependency_overrides[get_current_active_user] = lambda: object()
    tools = list(api_tools(app).values())
    message = 'Tra ma MCB LS, chi lay ma, thong so va gia, khong thiet ke'
    calls = []
    blocked = []
    def forbid(name):
        def denied(*args, **kwargs):
            blocked.append(name)
            raise AssertionError('Unexpected CAD lookup: ' + name)
        return denied
    report = {'scope': 'local API tools and real database; excludes model inference and network tunnel'}
    async with AsyncSessionLocal() as db, AsyncExitStack() as guards:
        for name in ['app.api.v1.endpoints.cad_library.manifest',
                     'app.api.v1.endpoints.cad_library.resolve_model_asset',
                     'app.services.cad.catalogtb_assets.assets',
                     'app.services.catalogtb_browser.browser_data']:
            guards.enter_context(patch(name, side_effect=forbid(name)))
        async def invoke(path, query):
            tool = next(t for t in tools if t['path'] == path and t['method'] == 'GET')
            assert permits_tool(tool, message), path
            assert not requires_cad(tool), path
            started = time.perf_counter()
            result = await execute_api_tool(app, db, 0, 0, tool, {'query': query}, {})
            duration = (time.perf_counter()-started)*1000
            calls.append({'path': path, 'milliseconds': round(duration, 2)})
            assert result['ok'], result
            return result['data'], duration
        brands, _ = await invoke('/api/v1/devices/brands', {})
        ls = [row for row in brands if row['name'].upper().startswith(('LS (', 'LS ELECTRIC')) or row['name'].upper() == 'LS']
        assert ls, 'No LS brand'
        durations = []
        for _ in range(5):
            models, ms1 = await invoke('/api/v1/devices/models', {'q':'MCB', 'brand_ids': ','.join(str(b['id']) for b in ls), 'include_cad':False, 'limit':30})
            prices, ms2 = await invoke('/api/v1/device-catalog', {'brand':'LS','category':'MCB','limit':30})
            assert models and prices['items'], 'No MCB LS results'
            assert all(m['brand_name'].upper().startswith(('LS (', 'LS ELECTRIC')) or m['brand_name'].upper() == 'LS' for m in models)
            assert all(not m['parameters'].get('cad') for m in models)
            durations.append(ms1+ms2)
        report.update(model_count=len(models), price_total=prices['total'],
                      positive_price_rows=sum(isinstance(r.get('price'),(int,float)) and r['price']>0 for r in prices['items']),
                      first_ms=round(durations[0],2), warm_median_ms=round(statistics.median(durations[1:]),2),
                      cad_attempts=blocked, calls=calls,
                      samples=[{k:r.get(k) for k in ('sku','brand','category','price','specifications','columns','cells')} for r in prices['items'][:3]])
    output = Path(__file__).resolve().parents[2] / 'reports' / 'mcb-ls-text-probe.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    asyncio.run(main())

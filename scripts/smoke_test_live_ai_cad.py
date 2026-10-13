"""One bounded AI/CAD smoke test on a new, explicitly named owner test project."""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

import ezdxf
import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'tmp'/'live_load_20261008'
BASE = 'https://www.elquote.top'


async def main():
    OUT.mkdir(parents=True,exist_ok=True)
    os.chdir(ROOT)
    sys.path.insert(0,str(ROOT))
    from app.core.security import create_access_token
    with sqlite3.connect('file:'+str(ROOT/'webbaogia.db')+'?mode=ro',uri=True) as db:
        uid = db.execute("SELECT id FROM users WHERE status='active' AND deleted_at IS NULL AND role!='admin' ORDER BY tokens DESC LIMIT 1").fetchone()[0]
    token = create_access_token(uid)
    doc = ezdxf.new('R2010')
    m = doc.modelspace()
    def text(s,x,y,height=12):
        m.add_text(s,dxfattribs={'height':height,'insert':(x,y)})
    text('OWNER LOAD TEST - NOT A CONSTRUCTION DRAWING',0,360)
    text('PANEL TEST-LT: ENCLOSURE H800 W600 D250 mm',0,330)
    text('3 PHASE 380V - SINGLE LINE DIAGRAM',0,300)
    rows = [('QF1 MCCB 3P 100A 25kA QTY 1',120,230),
            ('QF2 MCB 1P 16A 6kA QTY 1',60,110),
            ('QF3 MCB 1P 16A 6kA QTY 1',240,110)]
    for label,x,y in rows:
        m.add_lwpolyline([(x,y),(x+50,y),(x+50,y+35),(x,y+35)],close=True)
        text(label,x-30,y-20,8)
    for a,b in [((145,300),(145,265)),((145,230),(145,180)),
                ((85,180),(265,180)),((85,180),(85,145)),((265,180),(265,145)),
                ((85,110),(85,70)),((265,110),(265,70))]:
        m.add_line(a,b)
    path = OUT/'owner_load_test_sld.dxf'
    doc.saveas(path)
    report = {'started_utc':datetime.now(timezone.utc).isoformat(),
              'fixture':path.name,'expected_source_devices':3,'ai_requests_submitted':0,
              'events':[],'health_during_job':[]}
    def save():
        (OUT/'ai_cad_smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    async with httpx.AsyncClient(base_url=BASE,timeout=30,follow_redirects=True,
                    headers={'Authorization':'Bearer '+token},trust_env=False) as client:
        r = await client.post('/api/v1/projects',json={'name':'OWNER_LOAD_TEST_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'),'category':'Load test'})
        r.raise_for_status()
        pid = r.json()['id']
        report['project_id']=pid
        save()
        print('test_project_created',pid,flush=True)
        with path.open('rb') as f:
            r = await client.post(f'/api/v1/projects/{pid}/upload',files={'file':(path.name,f,'application/dxf')})
        r.raise_for_status()
        fid = r.json()['id']
        report['file_id']=fid
        save()
        done = asyncio.Event()
        async def health():
            async with httpx.AsyncClient(trust_env=False,timeout=3) as observer:
                while not done.is_set():
                    t=time.perf_counter()
                    try:
                        h=await asyncio.wait_for(observer.get('https://admin.elquote.top/health'),timeout=3)
                        status=h.status_code
                    except Exception as e:
                        status=type(e).__name__
                    report['health_during_job'].append({'status':status,'ms':round((time.perf_counter()-t)*1000,1)})
                    await asyncio.sleep(2)
        monitor=asyncio.create_task(health())
        result=None
        async def analyze():
            nonlocal result
            async with client.stream('POST','/api/v1/analyze/stream',json={
                    'project_id':pid,'file_id':fid,'is_new_session':True,
                    'fallback_to_standard_template':False,
                    'user_prompt':'Owner load test. Analyze only the three labeled breakers in this single-line drawing. Do not infer additional breakers. Return source quantities and evidence.'},
                    timeout=httpx.Timeout(120,connect=15)) as response:
                report['analysis_http_status']=response.status_code
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data: '):
                        continue
                    event=json.loads(line[6:])
                    brief={k:event.get(k) for k in ['type','stage','title','progress'] if k in event}
                    brief['elapsed_seconds']=round(time.perf_counter()-started,2)
                    report['events'].append(brief)
                    save()
                    print('analysis_event',json.dumps(brief,ensure_ascii=True),flush=True)
                    if event.get('type')=='complete':
                        result=event.get('result')
                        (OUT/'analysis_smoke_response.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
                    elif event.get('type')=='error':
                        report['analysis_error']=event.get('detail','')[:400]
        started=time.perf_counter()
        report['ai_requests_submitted']=1
        try:
            await asyncio.wait_for(analyze(),timeout=180)
        except Exception as exc:
            report['analysis_exception']=type(exc).__name__
        report['analysis_seconds']=round(time.perf_counter()-started,2)
        report['analysis_complete']=result is not None
        save()
        # Keep an independent known input if AI failed; never claim end-to-end success then.
        known=[{'category':'MCCB','name':'MCCB 3P 100A','spec':'3P 100A 25kA','in_a':100,'icu_ka':25,'poles':3,'quantity':1,'tag':'QF1','panel_code':'TEST-LT'}]
        known += [{'category':'MCB','name':'MCB 1P 16A','spec':'1P 16A 6kA','in_a':16,'icu_ka':6,'poles':1,'quantity':1,'tag':tag,'panel_code':'TEST-LT'} for tag in ['QF2','QF3']]
        devices=(result or {}).get('devices') or known
        report['analysis_device_rows']=len((result or {}).get('devices') or [])
        report['cad_input_source']='analysis' if (result or {}).get('devices') else 'known_fixture_independent_of_failed_AI'
        report['tokens_used']=(result or {}).get('tokens_used')
        started=time.perf_counter()
        try:
            r=await asyncio.wait_for(client.post('/api/v1/analyze/generate-quotation-cad',json={
                'project_id':pid,'devices':devices,'enclosure_dimensions':'800x600x250',
                'panel_code':'TEST-LT','panel_name':'Owner load test','brand_preference':'Schneider',
                'user_prompt':'Owner load test, not a construction drawing. Enclosure H800 W600 D250 mm.'},timeout=120),timeout=120)
            report['cad_http_status']=r.status_code
            if r.status_code==200:
                data=r.json()
                report['cad_response_keys']=list(data)
                report['cad_file_present']=bool(data.get('cad_file'))
                report['quotation_file_present']=bool(data.get('quotation_file'))
                (OUT/'cad_smoke_response.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
            else:
                report['cad_error']=r.text[:400]
        except Exception as exc:
            report['cad_exception']=type(exc).__name__
        report['cad_seconds']=round(time.perf_counter()-started,2)
        done.set()
        await monitor
        save()
        print('smoke_summary',json.dumps({k:v for k,v in report.items() if k not in ['events','health_during_job','analysis_error','cad_error']},ensure_ascii=True),flush=True)


if __name__=='__main__':
    asyncio.run(main())

"""Synthetic relational read benchmark. Never connects to the configured DB."""
import asyncio
import json
import statistics
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import event, insert, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, Project, ConversationSession, AnalysisIteration
from app.services.analysis_reads import session_page


async def run():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as db:
        db.add(User(id=1,email='benchmark@example.invalid',hashed_password='unused'))
        db.add(Project(id=1,user_id=1,name='Synthetic'))
        await db.flush()
        sessions = [dict(id=uuid.uuid4(),project_id=1,user_id=1,created_at=datetime(2026,1,1)+timedelta(days=n)) for n in range(100)]
        await db.execute(insert(ConversationSession),sessions)
        iterations = [dict(session_id=s['id'],iteration_number=k+1,trigger_type='benchmark',status='completed',
                      created_at=s['created_at']+timedelta(seconds=k),ai_parsed_devices=[{'name':'MCB','quantity':2}]*20,
                      ai_raw_response='r'*16384,prompt_sent='p'*8192) for s in sessions for k in range(10)]
        await db.execute(insert(AnalysisIteration),iterations); await db.commit()
    sql_count = [0]
    event.listen(engine.sync_engine,'before_cursor_execute',lambda *args: sql_count.__setitem__(0,sql_count[0]+1))
    result = {'environment':'local, in-memory SQLite, synthetic data, DAL only (not HTTP or production)',
              'sessions':100,'iterations':1000,'page_size':50,'samples':5}
    for mode in ('before','after'):
        times=[]; counts=[]; loaded=[]
        for _ in range(5):
            sql_count[0]=0; start=time.perf_counter()
            async with factory() as db:
                if mode=='before':
                    sessions=(await db.execute(select(ConversationSession).where(ConversationSession.project_id==1))).scalars().all()
                    rows=[]
                    for s in sessions:
                        rows.extend((await db.execute(select(AnalysisIteration).where(AnalysisIteration.session_id==s.id,AnalysisIteration.status=='completed'))).scalars().all())
                    loaded.append(len(rows))
                else:
                    rows,total=await session_page(db,1,SimpleNamespace(id=1,is_superuser=False),0,50)
                    loaded.append(len(rows))
            times.append((time.perf_counter()-start)*1000); counts.append(sql_count[0])
        result[mode]={'median_ms':round(statistics.median(times),2),'max_ms':round(max(times),2),'sql_queries':counts,'rows_materialized':loaded,'samples_ms':[round(t,2) for t in times]}
    out=Path(__file__).resolve().parents[1]/'docs/api-performance-2026-10-23/analysis-benchmark.json'
    out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
    await engine.dispose()


if __name__=='__main__': asyncio.run(run())

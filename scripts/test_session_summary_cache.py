import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base,User,Project,ConversationSession,AnalysisIteration
from app.services.analysis_reads import session_page


class SessionSummaryCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_database_cache_reuses_summary_and_invalidates_updated_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=create_async_engine('sqlite+aiosqlite:///'+str(Path(folder)/'history.db'))
            try:
                async with engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
                factory=async_sessionmaker(engine,expire_on_commit=False)
                async with factory() as db:
                    db.add(User(id=1,email='history@test.invalid',hashed_password='unused'))
                    db.add(Project(id=1,name='Test',user_id=1))
                    await db.flush()
                    sid=uuid.uuid4()
                    db.add(ConversationSession(id=sid,project_id=1,user_id=1))
                    await db.flush()
                    db.add(AnalysisIteration(id=1,session_id=sid,trigger_type='test',status='completed',
                           ai_parsed_devices=[{'quantity':2,'panel_code':'AP1','evidence_image':'heavy-image'}]))
                    await db.commit()
                queries=[]
                event.listen(engine.sync_engine,'before_cursor_execute',lambda c,cur,s,p,ctx,m:queries.append(s))
                user=SimpleNamespace(id=1,is_superuser=False)
                async with factory() as db:
                    first,_=await session_page(db,1,user)
                    self.assertEqual(first[0][0].ai_parsed_devices[0]['quantity'],2)
                queries.clear()
                async with factory() as db:
                    second,_=await session_page(db,1,user)
                    self.assertEqual(len(queries),3)
                    self.assertNotIn('ai_parsed_devices',' '.join(queries))
                    self.assertEqual(first[0][0].ai_parsed_devices,second[0][0].ai_parsed_devices)
                    await db.execute(update(AnalysisIteration).where(AnalysisIteration.id==1).values(
                        ai_parsed_devices=[{'quantity':3,'panel_code':'AP1'}]))
                    await db.commit()
                async with factory() as db:
                    changed,_=await session_page(db,1,user)
                    self.assertEqual(changed[0][0].ai_parsed_devices[0]['quantity'],3)
            finally:await engine.dispose()


if __name__=='__main__':unittest.main()

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from sqlalchemy import event, inspect, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from fastapi import HTTPException
from app.models import Base, User, Project, ConversationSession, AnalysisIteration, ProjectFile
from app.services.analysis_reads import session_page, latest_analysis


class AnalysisReadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.user = SimpleNamespace(id=1, is_superuser=False)
        async with self.factory() as db:
            db.add(User(id=1, email='audit@example.invalid', hashed_password='unused'))
            db.add(Project(id=1, user_id=1, name='Audit'))
            await db.flush()
            self.session_ids = []
            for n in range(12):
                sid = uuid.uuid4(); self.session_ids.append(sid)
                db.add(ConversationSession(id=sid, project_id=1, user_id=1,
                       created_at=datetime(2026, 1, 1) + timedelta(days=n)))
                await db.flush()
                for k in range(3):
                    db.add(AnalysisIteration(session_id=sid, iteration_number=k+1,
                           trigger_type='test', status='completed',
                           created_at=datetime(2026, 1, 1)+timedelta(days=n, seconds=k),
                           ai_parsed_devices=[{'name':'MCB','quantity':2}] if k<2 else [],
                           ai_raw_response='x'*8000, prompt_sent='private prompt'))
            await db.commit()
        self.queries = []
        event.listen(self.engine.sync_engine, 'before_cursor_execute',
                     lambda c, cur, statement, params, context, many: self.queries.append(statement))

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_constant_query_count_and_lightweight_page(self):
        async with self.factory() as db:
            rows, total = await session_page(db, 1, self.user, 0, 5)
            self.assertEqual(total,36); self.assertEqual(len(rows),5)
            self.assertEqual(len(self.queries),3)
            self.assertIn('ai_raw_response', inspect(rows[0][0]).unloaded)
            self.assertIn('prompt_sent', inspect(rows[0][0]).unloaded)
            self.assertIn('LIMIT', self.queries[-1])
            first_ids = {it.id for it, session in rows}
            second, _ = await session_page(db,1,self.user,5,5)
            self.assertFalse(first_ids & {it.id for it,session in second})

    async def test_latest_prefers_nonempty_and_only_one_result(self):
        async with self.factory() as db:
            sid, iteration, cad = await latest_analysis(db,1,self.user)
            self.assertEqual(sid,self.session_ids[-1])
            self.assertEqual(iteration.iteration_number,2)
            self.assertIn('ai_raw_response',inspect(iteration).unloaded)
            self.assertTrue(all('LIMIT' in q for q in self.queries[1:]))

    async def test_session_history_excludes_images_and_preserves_panel_counts(self):
        from sqlalchemy import update
        async with self.factory() as db:
            await db.execute(update(AnalysisIteration).values(
                ai_parsed_devices=[{'quantity':3,'panel_code':'AP1','panel_name':'Panel',
                                    'evidence_image':'data:image/png;base64,'+'A'*1000000}],
                confidence_scores={'panel_info':{'panel_code':'AP1'},'panel_images':{'default':'large-image'}}))
            await db.commit()
        async with self.factory() as db:
            rows, total = await session_page(db,1,self.user,0,5)
            self.assertEqual(total,36)
            for iteration, session in rows:
                self.assertEqual(iteration.ai_parsed_devices,[{'panel_code':'AP1','panel_name':'Panel','quantity':3}])
                self.assertEqual(iteration.confidence_scores['panel_info'],{'panel_code':'AP1'})
                self.assertNotIn('panel_images',iteration.confidence_scores)

    async def test_null_device_payload_is_an_empty_history_entry(self):
        from sqlalchemy import update
        async with self.factory() as db:
            await db.execute(update(AnalysisIteration).values(ai_parsed_devices=None))
            await db.commit()
        async with self.factory() as db:
            rows, _ = await session_page(db,1,self.user,0,5)
            self.assertTrue(all(it.ai_parsed_devices == [] for it, session in rows))

    async def test_other_user_cannot_read_project(self):
        async with self.factory() as db:
            with self.assertRaises(HTTPException) as error:
                await session_page(db,1,SimpleNamespace(id=2,is_superuser=False))
            self.assertEqual(error.exception.status_code,404)

    async def test_latest_falls_back_when_all_results_empty(self):
        from sqlalchemy import update
        async with self.factory() as db:
            await db.execute(update(AnalysisIteration).values(ai_parsed_devices=[]))
            await db.commit()
        async with self.factory() as db:
            _, iteration, _ = await latest_analysis(db,1,self.user)
            self.assertEqual(iteration.iteration_number,3)


if __name__ == '__main__': unittest.main()

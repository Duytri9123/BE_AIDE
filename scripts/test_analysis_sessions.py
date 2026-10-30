"""Session operations use a bounded number of queries and never load AI logs."""
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import event, inspect, select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Base, User, Project, ConversationSession, AnalysisIteration, ProjectFile
from app.services.analysis_sessions import (
    iteration_detail, remove_iteration, remove_project_sessions, cleanup_session_files,
)


class SessionOperationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        @event.listens_for(self.engine.sync_engine, 'connect')
        def foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.factory = async_sessionmaker(self.engine, expire_on_commit=False, autoflush=False)
        self.user = SimpleNamespace(id=1, is_superuser=False)
        self.sid, self.other_sid = uuid.uuid4(), uuid.uuid4()
        async with self.factory() as db:
            db.add(User(id=1, email='sessions@example.invalid', hashed_password='unused'))
            await db.flush()
            db.add_all([Project(id=1, user_id=1, name='Target'), Project(id=2, user_id=1, name='Other')])
            await db.flush()
            db.add_all([ConversationSession(id=self.sid, project_id=1, user_id=1),
                        ConversationSession(id=self.other_sid, project_id=2, user_id=1)])
            await db.flush()
            db.add_all([AnalysisIteration(id=i, session_id=self.sid if i < 121 else self.other_sid,
                        iteration_number=i, trigger_type='test', status='completed',
                        ai_parsed_devices=[{'name': 'MCB', 'quantity': 2}], confidence_scores={},
                        ai_raw_response='x' * 8000, prompt_sent='prompt' * 1000) for i in range(1, 122)])
            for i, (project, filename) in enumerate([(1, 'source.pdf'), (1, 'BanVe_Test.dxf'),
                    (1, 'BaoGia_Test.xlsx'), (2, 'BanVe_Other.dxf')], 1):
                db.add(ProjectFile(id=i, project_id=project, filename=filename,
                       file_path=f'/test/{filename}', file_size=1, file_type='test'))
            await db.commit()
        self.queries = []
        event.listen(self.engine.sync_engine, 'before_cursor_execute',
                     lambda c, cur, sql, params, ctx, many: self.queries.append(sql))

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_detail_does_not_fetch_prompts_or_all_cad_files(self):
        async with self.factory() as db:
            iteration, cad = await iteration_detail(db, 1, self.user)
            self.assertEqual(iteration.id, 1)
            self.assertEqual(cad.filename, 'BanVe_Test.dxf')
            self.assertTrue({'prompt_sent', 'ai_raw_response', 'ai_thinking'} <= inspect(iteration).unloaded)
            self.assertEqual(len(self.queries), 3)
            self.assertIn('LIMIT', self.queries[-1])

    async def test_delete_one_preserves_other_iterations_with_autoflush_disabled(self):
        async with self.factory() as db:
            await remove_iteration(db, 1, self.user)
            self.assertEqual(len(self.queries), 4)
            self.assertNotIn('ai_parsed_devices', '\n'.join(self.queries))
            self.assertIsNone(await db.get(AnalysisIteration, 1))
            self.assertIsNotNone(await db.get(ConversationSession, self.sid))
            self.assertEqual((await db.execute(select(func.count(AnalysisIteration.id)))).scalar_one(), 120)

    async def test_delete_last_removes_empty_session_without_nulling_foreign_keys(self):
        async with self.factory() as db:
            await remove_iteration(db, 121, self.user)
            self.assertIsNone(await db.get(ConversationSession, self.other_sid))
            self.assertIsNotNone(await db.get(ConversationSession, self.sid))

    async def test_bulk_delete_has_constant_queries_preserves_sources_and_other_projects(self):
        async with self.factory() as db:
            paths = await remove_project_sessions(db, 1, self.user)
            self.assertEqual(len(self.queries), 5)
            self.assertNotIn('ai_parsed_devices', '\n'.join(self.queries))
            self.assertEqual(set(paths), {'/test/BanVe_Test.dxf', '/test/BaoGia_Test.xlsx'})
            self.assertEqual((await db.execute(select(AnalysisIteration.id))).scalars().all(), [121])
            self.assertEqual(set((await db.execute(select(ProjectFile.id))).scalars()), {1, 4})
            self.assertIsNone(await db.get(ConversationSession, self.sid))

    async def test_unauthorized_user_cannot_read_or_delete(self):
        user = SimpleNamespace(id=2, is_superuser=False)
        for operation, identifier in [(iteration_detail, 1), (remove_iteration, 1), (remove_project_sessions, 1)]:
            async with self.factory() as db:
                with self.assertRaises(HTTPException) as error:
                    await operation(db, identifier, user)
                self.assertEqual(error.exception.status_code, 404)
                self.assertFalse(any(sql.startswith('DELETE') for sql in self.queries))

    def test_file_cleanup_handles_missing_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'generated.dxf'
            path.write_text('test')
            cleanup_session_files([str(path), str(path), str(path) + '.missing', None])
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()

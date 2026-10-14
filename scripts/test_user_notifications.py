import unittest
from types import SimpleNamespace
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy import select
from app.models.user import User
from app.models.notification import Notification
from app.api.v1.endpoints.notifications import inbox,read_all,read_one


class NotificationIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as db:
            await db.run_sync(User.__table__.create)
            await db.run_sync(Notification.__table__.create)
        self.session=async_sessionmaker(self.engine,expire_on_commit=False)()
        self.session.add_all([User(id=1,email='one@test.invalid',hashed_password='test'),User(id=2,email='two@test.invalid',hashed_password='test')])
        await self.session.flush()
        self.session.add_all([Notification(id=1,user_id=1,title='Own',body='Own body'),Notification(id=2,user_id=2,title='Other',body='Private')])
        await self.session.commit()
        self.user=SimpleNamespace(id=1)

    async def asyncTearDown(self):
        await self.session.close();await self.engine.dispose()

    async def test_inbox_does_not_expose_other_user(self):
        data=await inbox(limit=20,db=self.session,user=self.user)
        self.assertEqual(data['unread_count'],1)
        self.assertEqual([r['id'] for r in data['items']],[1])

    async def test_read_other_users_notification_is_rejected(self):
        with self.assertRaises(HTTPException) as context:await read_one(2,db=self.session,user=self.user)
        self.assertEqual(context.exception.status_code,404)
        self.assertFalse((await self.session.execute(select(Notification).where(Notification.id==2))).scalar_one().is_read)

    async def test_read_all_only_changes_own_inbox(self):
        await read_all(db=self.session,user=self.user)
        data=await inbox(limit=20,db=self.session,user=self.user)
        self.assertEqual(data['unread_count'],0)
        self.assertFalse((await self.session.execute(select(Notification).where(Notification.id==2))).scalar_one().is_read)

    async def test_read_one_is_idempotent(self):
        await read_one(1,db=self.session,user=self.user)
        await read_one(1,db=self.session,user=self.user)
        self.assertEqual((await inbox(limit=20,db=self.session,user=self.user))['unread_count'],0)


if __name__=='__main__':unittest.main()

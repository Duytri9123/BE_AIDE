from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from app.api.v1.endpoints.plans import get_my_subscription


def scalar_result(value):
    result=MagicMock()
    result.scalar_one_or_none.return_value=value
    return result


def empty_logs():
    result=MagicMock()
    result.scalars.return_value.all.return_value=[]
    return result


class CurrentPricingPlanTests(IsolatedAsyncioTestCase):
    async def test_paid_plan_returns_plan_id_independent_of_subscription_id_and_name(self):
        now=datetime.now(timezone.utc)
        subscription=SimpleNamespace(id=91,plan_id=7,starts_at=now-timedelta(days=1),
            ends_at=now+timedelta(days=30),status='active')
        db=AsyncMock()
        db.execute.side_effect=[scalar_result(subscription),scalar_result(SimpleNamespace(name='Gói đã đổi tên')),empty_logs()]
        result=await get_my_subscription(SimpleNamespace(id=5,tokens=3000),db)
        self.assertEqual(result.current_plan_id,7)
        self.assertEqual(result.active_subscription['plan_id'],7)
        self.assertEqual(result.active_subscription['id'],91)
        # The actual query excludes expired and not-yet-started subscriptions.
        statement=db.execute.call_args_list[0].args[0]
        query=str(statement)
        self.assertIn('subscriptions.ends_at >',query)
        self.assertIn('subscriptions.starts_at <=',query)
        self.assertEqual(statement.compile().params['starts_at_1'],statement.compile().params['ends_at_1'])

    async def test_no_valid_subscription_uses_backend_free_plan_id(self):
        db=AsyncMock()
        db.execute.side_effect=[scalar_result(None),scalar_result(12),empty_logs()]
        result=await get_my_subscription(SimpleNamespace(id=5,tokens=999999),db)
        self.assertEqual(result.current_plan_id,12)
        self.assertIsNone(result.active_subscription)
        self.assertIn('plans.price =',str(db.execute.call_args_list[1].args[0]))

    async def test_no_free_plan_does_not_invent_a_current_plan(self):
        db=AsyncMock()
        db.execute.side_effect=[scalar_result(None),scalar_result(None),empty_logs()]
        result=await get_my_subscription(SimpleNamespace(id=5,tokens=0),db)
        self.assertIsNone(result.current_plan_id)

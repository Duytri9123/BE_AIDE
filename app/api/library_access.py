"""Server-side entitlement for private library data and CAD assets."""
from collections import defaultdict, deque
from datetime import datetime, timezone
from time import monotonic
import re
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.payment import Payment

_requests = defaultdict(deque)

async def library_entitlement(user: User = Depends(get_current_active_user), db=Depends(get_db)):
    if user.role == 'library_reviewer':
        return {'full_access': True, 'reason': 'library_reviewer'}
    if user.is_superuser or user.role == 'admin':
        return {'full_access': True, 'reason': 'admin'}
    now=datetime.now(timezone.utc)
    stmt=(select(Subscription.id).join(Plan,Plan.id==Subscription.plan_id)
          .join(Payment,(Payment.user_id==Subscription.user_id)&(Payment.plan_id==Plan.id))
          .where(Subscription.user_id==user.id,Subscription.status=='active',
                 Subscription.starts_at<=now,Subscription.ends_at>now,
                 Plan.is_active.is_(True),Plan.price>0,Payment.status=='completed',
                 Payment.amount>=Plan.price,Payment.payment_method!='Hệ thống DGP')
          .limit(1))
    paid=(await db.execute(stmt)).scalar_one_or_none() is not None
    return {'full_access':paid,'reason':'paid' if paid else 'upgrade_required'}

async def require_library_access(request: Request,
                                 user: User=Depends(get_current_active_user),
                                 entitlement=Depends(library_entitlement)):
    # Free can browse and view raster previews, never CAD, manifests or insertion data.
    equipment_path = request.url.path.split('/equipment-library/', 1)[-1]
    free_view = (request.method == 'GET' and '/equipment-library/' in request.url.path
                 and (equipment_path in ('browse', 'browser-data') or
                      re.fullmatch(r'TB-[0-9a-f]{16}(?:/(?:preview|drawing-source|views/[^/]+/preview))?', equipment_path)))
    if not entitlement['full_access'] and not free_view:
        raise HTTPException(403,detail='Gói Free được xem thư viện. Nâng cấp để tải hoặc chèn CAD.',
                            headers={'Cache-Control':'private, no-store'})
    if not user.is_superuser and user.role!='admin':
        now=monotonic();queue=_requests[user.id]
        while queue and queue[0]<now-60:queue.popleft()
        if len(queue)>=120:
            raise HTTPException(429,'Quá nhiều yêu cầu thư viện. Vui lòng thử lại sau.',headers={'Retry-After':'60'})
        queue.append(now)
        # Avoid accumulating inactive identities in a long-running worker.
        if len(_requests)>10000:
            for key in list(_requests):
                if not _requests[key] or _requests[key][-1]<now-60:_requests.pop(key,None)
    return user

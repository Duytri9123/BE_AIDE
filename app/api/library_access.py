"""Server-side entitlement for private library data and CAD assets."""
from collections import defaultdict, deque
from time import monotonic
import re
from fastapi import Depends, HTTPException, Request
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User

_requests = defaultdict(deque)


def library_rate_bucket(method: str, path: str) -> str:
    # Raster thumbnails must not consume the product-list / metadata budget.
    if method == 'GET' and path.rstrip('/').endswith('/preview'):
        return 'preview'
    return 'read'


def allows_free_library_read(method: str, path: str) -> bool:
    equipment_path=path.split('/equipment-library/',1)[-1]
    return bool(method=='GET' and '/equipment-library/' in path and (
        equipment_path in ('browse','browser-data') or
        re.fullmatch(r'[^/]+/catalog-information',equipment_path) or
        re.fullmatch(r'(?:TB-[0-9a-f]{16}|[A-Z][A-Z0-9-]{2,95}-REFERENCE)(?:/(?:preview|drawing-source|views/[^/]+/preview))?',equipment_path)))

async def library_entitlement(user: User = Depends(get_current_active_user), db=Depends(get_db)):
    if user.role == 'library_reviewer':
        return {'full_access': True, 'reason': 'library_reviewer'}
    if user.is_superuser or user.role == 'admin':
        return {'full_access': True, 'reason': 'admin'}
    # Library viewing, downloads and insertion are available to active accounts.
    return {'full_access': True, 'reason': 'authenticated'}

async def require_library_access(request: Request,
                                 user: User=Depends(get_current_active_user),
                                 entitlement=Depends(library_entitlement)):
    # Free can browse public product information and raster previews.
    # CAD assets, manifests and insertion data still require full access.
    free_view = allows_free_library_read(request.method,request.url.path)
    if not entitlement['full_access'] and not free_view:
        raise HTTPException(403,detail='Gói Free được xem thư viện. Nâng cấp để tải hoặc chèn CAD.',
                            headers={'Cache-Control':'private, no-store'})
    if not user.is_superuser and user.role!='admin':
        now=monotonic();queue=_requests[(user.id,library_rate_bucket(request.method,request.url.path))]
        while queue and queue[0]<now-60:queue.popleft()
        if len(queue)>=120:
            raise HTTPException(429,'Quá nhiều yêu cầu thư viện. Vui lòng thử lại sau.',headers={'Retry-After':str(max(1,int(60-(now-queue[0]))+1))})
        queue.append(now)
        # Avoid accumulating inactive identities in a long-running worker.
        if len(_requests)>10000:
            for key in list(_requests):
                if not _requests[key] or _requests[key][-1]<now-60:_requests.pop(key,None)
    return user

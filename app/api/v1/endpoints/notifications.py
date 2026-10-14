"""Authenticated notification inbox; every operation is scoped to its owner."""
from datetime import timezone
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func,update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_active_user
from app.db.session import get_db
from app.models.notification import Notification

router=APIRouter()


@router.get('')
async def inbox(limit:int=Query(20,ge=1,le=50),db:AsyncSession=Depends(get_db),user=Depends(get_current_active_user)):
    owner=Notification.user_id==user.id
    unread=(await db.execute(select(func.count(Notification.id)).where(owner,Notification.is_read.is_(False)))).scalar_one()
    rows=(await db.execute(select(Notification).where(owner).order_by(Notification.created_at.desc(),Notification.id.desc()).limit(limit))).scalars().all()
    return {'unread_count':unread,'items':[{'id':n.id,'title':n.title,'body':n.body,'type':n.type,'link':n.link,
        'is_read':n.is_read,'created_at':n.created_at.replace(tzinfo=timezone.utc).isoformat() if n.created_at.tzinfo is None else n.created_at.isoformat()} for n in rows]}


@router.post('/read-all')
async def read_all(db:AsyncSession=Depends(get_db),user=Depends(get_current_active_user)):
    await db.execute(update(Notification).where(Notification.user_id==user.id,Notification.is_read.is_(False)).values(is_read=True))
    await db.commit()
    return {'status':'ok'}


@router.post('/{notification_id}/read')
async def read_one(notification_id:int,db:AsyncSession=Depends(get_db),user=Depends(get_current_active_user)):
    row=(await db.execute(select(Notification).where(Notification.id==notification_id,Notification.user_id==user.id))).scalar_one_or_none()
    if row is None:raise HTTPException(404,'Không tìm thấy thông báo.')
    row.is_read=True
    await db.commit()
    return {'status':'ok'}

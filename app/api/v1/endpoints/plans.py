from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.token_log import TokenLog

router = APIRouter()

# Schemas
class PlanOut(BaseModel):
    id: int
    name: str
    token_amount: int
    price: float
    duration_months: int
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

class SubscribeResponse(BaseModel):
    success: bool
    message: str
    tokens: int
    plan_name: str
    expires_at: datetime

class TokenLogOut(BaseModel):
    id: int
    amount_changed: int
    type: str
    description: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class MySubscriptionOut(BaseModel):
    current_tokens: int
    active_subscription: Optional[dict] = None
    recent_token_logs: List[TokenLogOut] = []

@router.get("", response_model=List[PlanOut])
async def get_active_plans(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách các gói cước đang kích hoạt để hiển thị lên bảng giá."""
    stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.price.asc())
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{plan_id}", response_model=PlanOut)
async def get_plan_by_id(plan_id: int, db: AsyncSession = Depends(get_db)):
    """Lấy thông tin chi tiết một gói cước."""
    stmt = select(Plan).where(Plan.id == plan_id)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Không tìm thấy gói cước")
    return plan

@router.post("/subscribe/{plan_id}", response_model=SubscribeResponse)
async def subscribe_plan(
    plan_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Đăng ký hoặc gia hạn gói cước:
    - Tạo bản ghi Subscription
    - Tạo bản ghi Payment
    - Cộng tokens vào tài khoản User
    - Ghi nhận nhật ký TokenLog
    """
    stmt = select(Plan).where(Plan.id == plan_id, Plan.is_active == True)
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Gói cước không tồn tại hoặc đã tạm dừng cung cấp")

    now = datetime.now(timezone.utc)
    duration_days = plan.duration_months * 30
    ends_at = now + timedelta(days=duration_days)

    # 1. Tạo bản ghi đăng ký gói
    subscription = Subscription(
        user_id=current_user.id,
        plan_id=plan.id,
        status="active",
        starts_at=now,
        ends_at=ends_at
    )
    db.add(subscription)

    # 2. Tạo bản ghi thanh toán
    payment = Payment(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=plan.price,
        payment_method="Hệ thống DGP",
        status="completed",
        transaction_reference=f"SUB-{current_user.id}-{int(now.timestamp())}"
    )
    db.add(payment)

    # 3. Cộng token vào tài khoản người dùng
    current_user.tokens = (current_user.tokens or 0) + plan.token_amount

    # 4. Ghi nhận TokenLog
    token_log = TokenLog(
        user_id=current_user.id,
        amount_changed=plan.token_amount,
        type="plan_subscription",
        description=f"Đăng ký thành công {plan.name} (+{plan.token_amount:,} tokens)"
    )
    db.add(token_log)

    await db.commit()
    await db.refresh(current_user)

    return SubscribeResponse(
        success=True,
        message=f"Đăng ký thành công {plan.name}! Bạn đã nhận được {plan.token_amount:,} tokens.",
        tokens=current_user.tokens,
        plan_name=plan.name,
        expires_at=ends_at
    )

@router.get("/user/my-subscription", response_model=MySubscriptionOut)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Lấy thông tin gói đang sử dụng và lịch sử token gần đây của user."""
    # Tìm subscription còn hạn mới nhất
    stmt_sub = (
        select(Subscription)
        .where(Subscription.user_id == current_user.id, Subscription.status == "active")
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    res_sub = await db.execute(stmt_sub)
    active_sub = res_sub.scalar_one_or_none()

    sub_data = None
    if active_sub:
        res_plan = await db.execute(select(Plan).where(Plan.id == active_sub.plan_id))
        plan = res_plan.scalar_one_or_none()
        sub_data = {
            "id": active_sub.id,
            "plan_name": plan.name if plan else "Gói dịch vụ",
            "starts_at": active_sub.starts_at,
            "ends_at": active_sub.ends_at,
            "status": active_sub.status
        }

    # Lấy 10 log token gần nhất
    stmt_logs = (
        select(TokenLog)
        .where(TokenLog.user_id == current_user.id)
        .order_by(desc(TokenLog.created_at))
        .limit(10)
    )
    res_logs = await db.execute(stmt_logs)
    token_logs = res_logs.scalars().all()

    return MySubscriptionOut(
        current_tokens=current_user.tokens or 0,
        active_subscription=sub_data,
        recent_token_logs=list(token_logs)
    )

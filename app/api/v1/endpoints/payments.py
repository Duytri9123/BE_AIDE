import re
import urllib.parse
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.plan import Plan
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.token_log import TokenLog
from app.models.notification import Notification
from app.models.system_setting import SystemSetting

logger = logging.getLogger("app.payments")
router = APIRouter()

# ==================== SCHEMAS ====================

class PaymentCreateRequest(BaseModel):
    plan_id: int

class PaymentCreateResponse(BaseModel):
    payment_id: int
    order_code: str
    plan_id: int
    plan_name: str
    amount: float
    bank_name: str
    account_number: str
    account_name: str
    qr_url: str
    vietqr_url: str
    status: str
    expires_at: datetime
    message: Optional[str] = None

class PaymentStatusResponse(BaseModel):
    payment_id: int
    order_code: str
    status: str  # pending, completed, cancelled, failed
    tokens: int
    plan_name: Optional[str] = None
    amount: float
    updated_at: Optional[datetime] = None

class SepayWebhookPayload(BaseModel):
    id: Optional[int] = None
    gateway: Optional[str] = None
    transactionDate: Optional[str] = None
    accountNumber: Optional[str] = None
    code: Optional[str] = None
    content: Optional[str] = ""
    transferType: Optional[str] = "in"
    transferAmount: Optional[float] = 0.0
    accumulated: Optional[float] = None
    referenceCode: Optional[str] = None
    description: Optional[str] = None

class PaymentHistoryItem(BaseModel):
    id: int
    order_code: str
    plan_name: str
    amount: float
    status: str
    payment_method: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ==================== HELPER FUNCTIONS ====================

async def get_sepay_config(db: AsyncSession) -> dict:
    """Lấy cấu hình ngân hàng SePay từ SystemSetting hoặc fallback về config settings."""
    cfg = {
        "api_key": settings.SEPAY_API_KEY,
        "bank_name": settings.SEPAY_BANK_NAME or "MBBank",
        "account_number": settings.SEPAY_ACCOUNT_NUMBER or "0388888888",
        "account_name": settings.SEPAY_ACCOUNT_NAME or "DGP ELECTRIC"
    }

    try:
        stmt = select(SystemSetting).where(
            SystemSetting.key.in_([
                "sepay_api_key",
                "sepay_bank_name",
                "sepay_account_number",
                "sepay_account_name"
            ])
        )
        res = await db.execute(stmt)
        for s in res.scalars().all():
            if s.key == "sepay_api_key" and s.value:
                cfg["api_key"] = s.value.strip()
            elif s.key == "sepay_bank_name" and s.value:
                cfg["bank_name"] = s.value.strip()
            elif s.key == "sepay_account_number" and s.value:
                cfg["account_number"] = s.value.strip()
            elif s.key == "sepay_account_name" and s.value:
                cfg["account_name"] = s.value.strip()
    except Exception as e:
        logger.warning(f"Lỗi khi đọc cấu hình SePay từ SystemSetting: {e}")

    return cfg

def build_qr_urls(bank_name: str, account_number: str, account_name: str, amount: float, order_code: str):
    """Tạo URL mã VietQR qua SePay và chuẩn VietQR."""
    amt_int = int(amount)
    des_enc = urllib.parse.quote(order_code)
    acc_name_enc = urllib.parse.quote(account_name)

    # 1. SePay QR Template
    sepay_qr = f"https://qr.sepay.vn/img?acc={account_number}&bank={bank_name}&amount={amt_int}&des={des_enc}&template=compact"

    # 2. Chuẩn VietQR fallback
    vietqr = f"https://img.vietqr.io/image/{bank_name}-{account_number}-compact2.png?amount={amt_int}&addInfo={des_enc}&accountName={acc_name_enc}"

    return sepay_qr, vietqr

# ==================== ENDPOINTS ====================

@router.post("/create", response_model=PaymentCreateResponse)
async def create_payment_order(
    req: PaymentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo đơn hàng thanh toán SePay (VietQR):
    - Nếu gói cước có giá 0đ (Gói miễn phí): Kích hoạt ngay lập tức.
    - Nếu gói cước có phí: Tạo bản ghi Payment 'pending', sinh mã định danh 'AIDE{payment_id}' và link VietQR.
    """
    stmt = select(Plan).where(Plan.id == req.plan_id, Plan.is_active == True)
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Gói cước không tồn tại hoặc đã tạm dừng cung cấp")

    now = datetime.now(timezone.utc)
    cfg = await get_sepay_config(db)

    # Xử lý gói miễn phí (0 VNĐ)
    if plan.price <= 0:
        duration_days = plan.duration_months * 30
        ends_at = now + timedelta(days=duration_days)

        subscription = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            status="active",
            starts_at=now,
            ends_at=ends_at
        )
        db.add(subscription)

        payment = Payment(
            user_id=current_user.id,
            plan_id=plan.id,
            amount=0.0,
            payment_method="Free Trial",
            status="completed",
            transaction_reference=f"FREE-{current_user.id}-{int(now.timestamp())}"
        )
        db.add(payment)

        current_user.tokens = (current_user.tokens or 0) + plan.token_amount

        token_log = TokenLog(
            user_id=current_user.id,
            amount_changed=plan.token_amount,
            type="plan_subscription",
            description=f"Kích hoạt miễn phí {plan.name} (+{plan.token_amount:,} tokens)"
        )
        db.add(token_log)

        await db.commit()
        await db.refresh(payment)

        return PaymentCreateResponse(
            payment_id=payment.id,
            order_code=payment.transaction_reference,
            plan_id=plan.id,
            plan_name=plan.name,
            amount=0.0,
            bank_name=cfg["bank_name"],
            account_number=cfg["account_number"],
            account_name=cfg["account_name"],
            qr_url="",
            vietqr_url="",
            status="completed",
            expires_at=ends_at,
            message=f"Đã kích hoạt thành công {plan.name}! Nhận ngay {plan.token_amount:,} tokens."
        )

    # Gói cước có phí: Tạo bản ghi Payment pending
    payment = Payment(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=plan.price,
        payment_method="sepay",
        status="pending",
        transaction_reference="TEMP"
    )
    db.add(payment)
    await db.flush()  # Flush để nhận payment.id

    order_code = f"AIDE{payment.id}"
    payment.transaction_reference = order_code
    await db.commit()
    await db.refresh(payment)

    # Thời hạn hiệu lực của đơn hàng (15 phút)
    expires_at = now + timedelta(minutes=15)

    sepay_qr, vietqr = build_qr_urls(
        bank_name=cfg["bank_name"],
        account_number=cfg["account_number"],
        account_name=cfg["account_name"],
        amount=payment.amount,
        order_code=order_code
    )

    return PaymentCreateResponse(
        payment_id=payment.id,
        order_code=order_code,
        plan_id=plan.id,
        plan_name=plan.name,
        amount=payment.amount,
        bank_name=cfg["bank_name"],
        account_number=cfg["account_number"],
        account_name=cfg["account_name"],
        qr_url=sepay_qr,
        vietqr_url=vietqr,
        status="pending",
        expires_at=expires_at,
        message="Vui lòng quét mã QR hoặc chuyển khoản với đúng nội dung để kích hoạt tự động."
    )

@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
async def check_payment_status(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Kiểm tra trạng thái đơn thanh toán (dành cho client polling realtime).
    """
    stmt = select(Payment).where(Payment.id == payment_id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng thanh toán")

    # Chỉ cho phép chính chủ hoặc admin xem
    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền truy cập đơn thanh toán này")

    plan_name = None
    if payment.plan_id:
        res_plan = await db.execute(select(Plan).where(Plan.id == payment.plan_id))
        plan = res_plan.scalar_one_or_none()
        if plan:
            plan_name = plan.name

    await db.refresh(current_user)

    return PaymentStatusResponse(
        payment_id=payment.id,
        order_code=payment.transaction_reference or f"AIDE{payment.id}",
        status=payment.status,
        tokens=current_user.tokens or 0,
        plan_name=plan_name,
        amount=payment.amount,
        updated_at=payment.updated_at
    )

@router.post("/sepay-webhook")
async def handle_sepay_webhook(
    payload: SepayWebhookPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    """
    Endpoint nhận Webhook tự động từ SePay khi có biến động số dư ngân hàng:
    - Xác thực Header Authorization nếu SEPAY_API_KEY đã được thiết lập.
    - Tìm kiếm mã đơn hàng AIDE{id} trong nội dung chuyển khoản.
    - Đối soát số tiền, cập nhật trạng thái completed.
    - Kích hoạt gói Subscription, cộng Tokens cho user và gửi thông báo.
    """
    cfg = await get_sepay_config(db)

    # 1. Xác thực API Key nếu có cấu hình
    expected_api_key = cfg.get("api_key")
    if expected_api_key:
        auth_header = authorization or request.headers.get("authorization", "")
        # SePay gửi format: "Apikey <TOKEN>" hoặc "Bearer <TOKEN>" hoặc token thuần
        clean_token = auth_header.replace("Apikey ", "").replace("apikey ", "").replace("Bearer ", "").strip()
        if clean_token != expected_api_key.strip():
            logger.warning(f"SePay Webhook rejected: Unauthorized token {auth_header}")
            raise HTTPException(status_code=401, detail="Xác thực Webhook không hợp lệ")

    # 2. Chỉ xử lý tiền vào (transferType == "in")
    if payload.transferType and payload.transferType.lower() != "in":
        logger.info(f"SePay Webhook ignored transferType: {payload.transferType}")
        return {"success": True, "message": "Bỏ qua giao dịch tiền ra"}

    # 3. Trích xuất mã đơn hàng từ nội dung chuyển khoản
    text_to_search = f"{payload.content or ''} {payload.description or ''} {payload.code or ''}"
    match = re.search(r"AIDE[-_\s]*(\d+)", text_to_search, re.IGNORECASE)

    payment: Optional[Payment] = None
    if match:
        payment_id = int(match.group(1))
        stmt = select(Payment).where(Payment.id == payment_id)
        res = await db.execute(stmt)
        payment = res.scalar_one_or_none()

    # Fallback: Tìm theo transaction_reference nếu match bằng chuỗi
    if not payment:
        stmt_pending = select(Payment).where(Payment.status == "pending")
        res_pending = await db.execute(stmt_pending)
        pending_list = res_pending.scalars().all()
        for p in pending_list:
            if p.transaction_reference and p.transaction_reference.upper() in text_to_search.upper():
                payment = p
                break

    if not payment:
        logger.warning(f"SePay Webhook: Không tìm thấy đơn hàng khớp với nội dung '{text_to_search}'")
        return {
            "success": False,
            "message": f"Không tìm thấy đơn hàng khớp với nội dung: {payload.content}"
        }

    # 4. Kiểm tra xem đơn đã hoàn tất trước đó chưa (Idempotency)
    if payment.status == "completed":
        logger.info(f"SePay Webhook: Đơn hàng {payment.id} đã hoàn tất từ trước")
        return {"success": True, "message": "Đơn hàng đã được ghi nhận hoàn tất trước đó"}

    # 5. Kiểm tra số tiền chuyển
    received_amount = float(payload.transferAmount or 0.0)
    if received_amount < payment.amount:
        logger.warning(f"SePay Webhook: Đơn #{payment.id} nhận {received_amount}đ, yêu cầu {payment.amount}đ")
        return {
            "success": False,
            "message": f"Số tiền chuyển ({received_amount:,.0f}đ) chưa đủ giá gói ({payment.amount:,.0f}đ)"
        }

    # 6. Kích hoạt đơn hàng & cộng tokens
    now = datetime.now(timezone.utc)
    payment.status = "completed"
    if payload.referenceCode:
        payment.transaction_reference = f"AIDE{payment.id}-{payload.referenceCode}"

    # Lấy User và Plan
    stmt_user = select(User).where(User.id == payment.user_id)
    res_user = await db.execute(stmt_user)
    target_user = res_user.scalar_one_or_none()

    stmt_plan = select(Plan).where(Plan.id == payment.plan_id)
    res_plan = await db.execute(stmt_plan)
    target_plan = res_plan.scalar_one_or_none()

    if target_user and target_plan:
        # Cộng token cho user
        target_user.tokens = (target_user.tokens or 0) + target_plan.token_amount

        # Tạo / gia hạn Subscription
        duration_days = target_plan.duration_months * 30
        ends_at = now + timedelta(days=duration_days)
        subscription = Subscription(
            user_id=target_user.id,
            plan_id=target_plan.id,
            status="active",
            starts_at=now,
            ends_at=ends_at
        )
        db.add(subscription)

        # Ghi nhật ký TokenLog
        token_log = TokenLog(
            user_id=target_user.id,
            amount_changed=target_plan.token_amount,
            type="plan_subscription",
            description=f"Thanh toán SePay thành công cho {target_plan.name} (+{target_plan.token_amount:,} tokens) - Mã GD: {payload.referenceCode or payload.id}"
        )
        db.add(token_log)

        # Tạo thông báo Notification trong hệ thống
        notification = Notification(
            user_id=target_user.id,
            title="Thanh toán thành công!",
            body=f"Bạn đã thanh toán thành công {target_plan.name}. Tài khoản đã được cộng {target_plan.token_amount:,} tokens!",
            type="payment_success"
        )
        db.add(notification)

    await db.commit()
    logger.info(f"SePay Webhook thành công: Đơn #{payment.id} đã hoàn tất, user #{payment.user_id} nhận {target_plan.token_amount if target_plan else 0} tokens")

    return {
        "success": True,
        "message": f"Thanh toán thành công cho đơn #{payment.id}"
    }

@router.post("/{payment_id}/cancel")
async def cancel_payment(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Người dùng hủy đơn thanh toán đang ở trạng thái pending."""
    stmt = select(Payment).where(Payment.id == payment_id, Payment.user_id == current_user.id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Chỉ có thể hủy đơn hàng đang chờ thanh toán")

    payment.status = "cancelled"
    await db.commit()
    return {"success": True, "message": "Đã hủy đơn hàng thành công"}

@router.get("/history", response_model=List[PaymentHistoryItem])
async def get_my_payment_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Lấy danh sách các giao dịch thanh toán của người dùng hiện tại."""
    stmt = (
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(desc(Payment.created_at))
        .limit(30)
    )
    res = await db.execute(stmt)
    payments = res.scalars().all()

    items = []
    for p in payments:
        plan_name = "Nạp dịch vụ"
        if p.plan_id:
            res_p = await db.execute(select(Plan.name).where(Plan.id == p.plan_id))
            pn = res_p.scalar_one_or_none()
            if pn:
                plan_name = pn

        items.append(
            PaymentHistoryItem(
                id=p.id,
                order_code=p.transaction_reference or f"AIDE{p.id}",
                plan_name=plan_name,
                amount=p.amount,
                status=p.status,
                payment_method=p.payment_method,
                created_at=p.created_at
            )
        )

    return items

@router.post("/test-simulate-success/{payment_id}")
async def simulate_test_payment_success(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    [Môi trường Test / Dev]
    Giả lập chuyển khoản thành công từ ngân hàng để kiểm tra toàn bộ luồng
    Frontend & Backend mà không cần tốn tiền thật.
    """
    stmt = select(Payment).where(Payment.id == payment_id)
    res = await db.execute(stmt)
    payment = res.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

    if payment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Không có quyền thao tác trên đơn hàng này")

    if payment.status == "completed":
        return {"success": True, "message": "Đơn hàng này đã hoàn tất từ trước"}

    # Giả lập payload từ SePay
    simulated_payload = SepayWebhookPayload(
        id=int(datetime.now().timestamp()),
        gateway="MBBank-SIMULATOR",
        transactionDate=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        accountNumber="0388888888",
        content=f"AIDE{payment.id} TEST CHUYEN KHOAN",
        transferType="in",
        transferAmount=payment.amount,
        referenceCode=f"TEST_REF_{int(datetime.now().timestamp())}"
    )

    # Tái sử dụng logic của webhook
    return await handle_sepay_webhook(
        payload=simulated_payload,
        request=Request({"type": "http", "headers": []}),
        db=db,
        authorization=None
    )

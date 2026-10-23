from sqladmin import ModelView
from wtforms import SelectField, PasswordField, validators
from markupsafe import Markup
from typing import Any
from starlette.requests import Request

from app.models.user import User
from app.core.security import get_password_hash


def format_user_subscription(m: User, a: Any) -> Markup:
    subs = getattr(m, "subscriptions", []) or []
    active_sub = None
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    for s in subs:
        if s.status == "active":
            if not s.ends_at:
                active_sub = s
                break
            ends = s.ends_at if s.ends_at.tzinfo else s.ends_at.replace(tzinfo=timezone.utc)
            if ends >= now:
                active_sub = s
                break
    if not active_sub and subs:
        active_sub = subs[0]

    if active_sub:
        pname = active_sub.plan.name if getattr(active_sub, "plan", None) else f"Gói #{active_sub.plan_id}"
        if active_sub.status == "active":
            ends_str = active_sub.ends_at.strftime("%d/%m/%Y") if active_sub.ends_at else "Vô thời hạn"
            return Markup(
                f'<div class="d-inline-flex flex-column">'
                f'<span class="badge bg-primary-soft text-primary fw-bold" style="font-size:11.5px;">{pname}</span>'
                f'<small class="text-muted mt-1" style="font-size:10.5px;"><i class="fa-regular fa-clock me-1"></i>HSD: {ends_str}</small>'
                f'</div>'
            )
        else:
            return Markup(f'<span class="badge bg-secondary-soft text-muted fw-bold" style="font-size:11px;">{pname} ({active_sub.status})</span>')
    return Markup('<span class="badge bg-light text-muted border fw-medium" style="font-size:11px;">Gói Cơ Bản (Free)</span>')


class UserAdmin(ModelView, model=User):
    name = "Người dùng"
    name_plural = "Người dùng"
    icon = "fa-solid fa-users"
    category = "Quản lý Người dùng"
    list_template = "users/list.html"
    edit_template = "users/edit.html"
    
    column_list = [
        User.id, 
        User.name, 
        User.email, 
        User.status, 
        User.role, 
        User.subscriptions, 
        User.tokens, 
        User.created_at
    ]
    column_searchable_list = [User.email, User.name]
    column_sortable_list = [User.id, User.email, User.tokens, User.created_at]
    column_default_sort = [(User.created_at, True)]
    
    column_labels = {
        User.id: "ID",
        User.name: "Tên người dùng",
        User.email: "Email",
        User.phone: "Số điện thoại",
        User.status: "Trạng thái",
        User.role: "Vai trò",
        User.subscriptions: "Gói cước / Dịch vụ",
        User.tokens: "Tokens",
        User.created_at: "Ngày tạo",
        User.updated_at: "Cập nhật"
    }
    
    column_formatters = {
        User.status: lambda m, a: Markup(
            f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else ("warning-soft text-warning" if m.status == "inactive" else "danger-soft text-danger")} fw-bold">'
            f'{"● Hoạt động" if m.status == "active" else ("○ Tạm dừng" if m.status == "inactive" else (m.status or "Khóa"))}'
            f'</span>'
        ),
        User.role: lambda m, a: Markup(
            f'<span class="badge bg-{"primary-soft text-primary" if m.role == "admin" else "secondary-soft text-muted"} fw-bold">'
            f'{"Quản trị viên" if m.role == "admin" else "Người dùng"}'
            f'</span>'
        ),
        User.subscriptions: format_user_subscription,
        User.tokens: lambda m, a: Markup(f'<span class="text-primary fw-bold"><i class="fa-solid fa-coins text-warning me-1"></i>{(m.tokens or 0):,}</span>'),
        User.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    
    form_columns = [
        User.name,
        User.email, 
        User.phone,
        User.status, 
        User.role, 
        User.tokens,
        "hashed_password"
    ]
    
    form_overrides = {
        "status": SelectField,
        "role": SelectField,
        "hashed_password": PasswordField
    }
    
    form_args = {
        "name": {"label": "Tên người dùng"},
        "email": {"label": "Địa chỉ Email"},
        "phone": {"label": "Số điện thoại"},
        "status": {
            "label": "Trạng thái tài khoản",
            "choices": [
                ("active", "Hoạt động (active)"),
                ("inactive", "Chưa kích hoạt (inactive)"),
                ("locked", "Đã khóa / Tạm dừng (locked)")
            ],
            "default": "active"
        },
        "role": {
            "label": "Vai trò hệ thống",
            "choices": [
                ("user", "Khách hàng / Người dùng (user)"),
                ("admin", "Quản trị viên (admin)")
            ],
            "default": "user"
        },
        "tokens": {"label": "Số lượng Tokens"},
        "hashed_password": {
            "label": "Mật khẩu (để trống nếu giữ nguyên)",
            "validators": [validators.Optional()]
        }
    }
    
    form_widget_args = {
        "status": {"class": "form-select"},
        "role": {"class": "form-select"}
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True
    
    page_size = 20
    page_size_options = [10, 20, 50, 100]

    def list_query(self, request: Request):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.subscription import Subscription
        return select(User).options(selectinload(User.subscriptions).selectinload(Subscription.plan))

    def details_query(self, request: Request):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.subscription import Subscription
        return select(User).options(selectinload(User.subscriptions).selectinload(Subscription.plan))

    def form_edit_query(self, request: Request):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.subscription import Subscription
        return select(User).options(selectinload(User.subscriptions).selectinload(Subscription.plan))

    async def edit_context(self, request: Request) -> dict[str, Any]:
        pk = request.path_params.get("pk")
        from app.models.plan import Plan
        from app.models.subscription import Subscription
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from datetime import datetime, timezone

        plans = []
        active_sub = None
        days_remaining = 0
        now = datetime.now(timezone.utc)

        try:
            async with self.session_maker() as session:
                res_plans = await session.execute(
                    select(Plan).where(Plan.is_active == True).order_by(Plan.price.asc())
                )
                plans = res_plans.scalars().all()

                if pk and str(pk).isdigit():
                    uid = int(pk)
                    res_sub = await session.execute(
                        select(Subscription)
                        .options(selectinload(Subscription.plan))
                        .where(Subscription.user_id == uid)
                        .order_by(Subscription.created_at.desc())
                    )
                    subs = res_sub.scalars().all()
                    for s in subs:
                        if s.status == "active":
                            active_sub = s
                            if s.ends_at:
                                ends = s.ends_at if s.ends_at.tzinfo else s.ends_at.replace(tzinfo=timezone.utc)
                                diff = (ends - now).days
                                days_remaining = max(0, diff)
                            break
                    if not active_sub and subs:
                        active_sub = subs[0]
                        days_remaining = 0
        except Exception as e:
            print(f"[UserAdmin.edit_context] Error: {e}")

        return {
            "available_plans": plans,
            "active_sub": active_sub,
            "days_remaining": days_remaining,
            "now": now
        }

    async def assign_user_plan(self, user_id: int, plan_id: int, duration_months: int = 0, add_tokens: bool = True) -> None:
        """Cấp hoặc đổi gói cước cho người dùng"""
        from app.models.plan import Plan
        from app.models.subscription import Subscription
        from app.models.payment import Payment
        from app.models.token_log import TokenLog
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import update

        async with self.session_maker() as session:
            user = await session.get(User, user_id)
            plan = await session.get(Plan, plan_id)
            if not user or not plan:
                return

            plan_name = str(plan.name)
            plan_tokens = int(plan.token_amount or 0)
            plan_price = float(plan.price or 0.0)
            now = datetime.now(timezone.utc)
            months = duration_months if duration_months > 0 else (plan.duration_months or 1)
            ends_at = now + timedelta(days=months * 30)

            # Đánh dấu các subscription active cũ thành replaced
            await session.execute(
                update(Subscription)
                .where(Subscription.user_id == user_id, Subscription.status == "active")
                .values(status="replaced")
            )

            # Tạo subscription mới
            new_sub = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                status="active",
                starts_at=now,
                ends_at=ends_at
            )
            session.add(new_sub)

            # Cộng tokens nếu được chọn
            if add_tokens and plan_tokens:
                user.tokens = (user.tokens or 0) + plan_tokens
                token_log = TokenLog(
                    user_id=user_id,
                    amount_changed=plan_tokens,
                    type="admin_grant",
                    description=f"Admin cấp {plan_name} (+{plan_tokens:,} tokens)"
                )
                session.add(token_log)

            # Ghi nhận lịch sử giao dịch
            payment = Payment(
                user_id=user_id,
                plan_id=plan.id,
                amount=plan_price,
                payment_method="manual",
                status="completed",
                transaction_reference=f"ADMIN-ASSIGN-{user_id}-{int(now.timestamp())}"
            )
            session.add(payment)
            await session.commit()
            print(f"[UserAdmin.assign_user_plan] Successfully assigned plan {plan_name} to user #{user_id}")

    async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request = None, **kwargs) -> None:
        if "hashed_password" in data:
            pwd = data["hashed_password"]
            if not pwd or not str(pwd).strip():
                # Khi chỉnh sửa: để trống mật khẩu thì giữ nguyên mật khẩu cũ, không ghi đè
                del data["hashed_password"]
            elif not str(pwd).startswith("$2"):
                data["hashed_password"] = get_password_hash(str(pwd))
        elif is_created:
            # Tạo mới người dùng nếu không nhập pass thì đặt mật khẩu mặc định
            data["hashed_password"] = get_password_hash("12345678")

    async def after_model_change(self, data: dict, model: Any, is_created: bool, request: Request = None, **kwargs) -> None:
        if request:
            try:
                form = await request.form()
                assign_plan_id = form.get("assign_plan_id")
                if assign_plan_id and str(assign_plan_id).isdigit():
                    plan_id = int(assign_plan_id)
                    if plan_id > 0:
                        duration_months = int(form.get("assign_duration_months") or 0)
                        add_tokens = form.get("assign_add_tokens") in ["1", "true", "on", True]
                        await self.assign_user_plan(model.id, plan_id, duration_months, add_tokens)
            except Exception as e:
                print(f"[UserAdmin.after_model_change] Error assigning plan: {e}")

    async def on_model_delete(self, model: User, request: Request = None, **kwargs) -> None:
        """Đảm bảo xóa sạch các dữ liệu phụ thuộc của user an toàn trước khi xóa User"""
        from sqlalchemy import text
        try:
            async with self.session_maker() as session:
                uid = model.id
                await session.execute(text("DELETE FROM user_profiles WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM refresh_tokens WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM subscriptions WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM payments WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM token_logs WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM activity_logs WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM user_device_libraries WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM user_library_files WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM conversation_sessions WHERE user_id = :uid"), {"uid": uid})
                await session.execute(text("DELETE FROM project_files WHERE project_id IN (SELECT id FROM projects WHERE user_id = :uid)"), {"uid": uid})
                await session.execute(text("DELETE FROM project_versions WHERE project_id IN (SELECT id FROM projects WHERE user_id = :uid)"), {"uid": uid})
                await session.execute(text("DELETE FROM projects WHERE user_id = :uid"), {"uid": uid})
                await session.commit()
        except Exception as e:
            # Log error if any and proceed with ORM cascade
            print(f"[UserAdmin.on_model_delete] Pre-cleanup note: {e}")

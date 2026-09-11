from sqladmin import ModelView
from markupsafe import Markup
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.token_log import TokenLog

class PlanAdmin(ModelView, model=Plan):
    name = "Gói cước"
    name_plural = "Gói cước"
    icon = "fa-solid fa-paper-plane"
    category = "Gói cước & Thanh toán"
    list_template = "billing/plans_list.html"
    
    column_list = [
        Plan.id,
        Plan.name,
        Plan.price,
        Plan.token_amount,
        Plan.duration_months,
        Plan.is_active,
        Plan.created_at
    ]
    column_searchable_list = [Plan.name, Plan.description]
    column_sortable_list = [Plan.id, Plan.name, Plan.price, Plan.token_amount, Plan.is_active, Plan.created_at]
    column_default_sort = [(Plan.price, False)]

    column_labels = {
        Plan.id: "ID",
        Plan.name: "Tên gói cước",
        Plan.price: "Đơn giá (VND)",
        Plan.token_amount: "Số lượng tokens",
        Plan.duration_months: "Thời hạn",
        Plan.description: "Mô tả / Quyền lợi",
        Plan.is_active: "Trạng thái",
        Plan.created_at: "Ngày tạo"
    }

    column_formatters = {
        Plan.name: lambda m, a: Markup(f'<span class="fw-bold text-dark">{m.name}</span>'),
        Plan.price: lambda m, a: Markup(f'<span class="badge bg-success-soft text-success fw-bold fs-7">{m.price:,.0f} đ</span>') if (m.price or 0) > 0 else Markup('<span class="badge bg-primary-soft text-primary fw-bold fs-7">Miễn phí</span>'),
        Plan.token_amount: lambda m, a: Markup(f'<span class="fw-bold text-primary"><i class="fa-solid fa-coins text-warning me-1"></i>{(m.token_amount or 0):,}</span>'),
        Plan.duration_months: lambda m, a: f"{m.duration_months} tháng" if m.duration_months else "Vô thời hạn",
        Plan.is_active: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.is_active else "danger-soft text-danger"} fw-bold">{"● Kích hoạt" if m.is_active else "○ Tạm khóa"}</span>'),
        Plan.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y") if m.created_at else "",
    }

    form_columns = [
        Plan.name,
        Plan.price,
        Plan.token_amount,
        Plan.duration_months,
        Plan.description,
        Plan.is_active
    ]

    form_args = {
        "name": {"label": "Tên gói cước"},
        "price": {"label": "Đơn giá (VND, nhập 0 nếu miễn phí)"},
        "token_amount": {"label": "Số lượng Token cấp khi đăng ký"},
        "duration_months": {"label": "Thời hạn sử dụng (tháng)"},
        "description": {"label": "Mô tả tính năng / quyền lợi (mỗi tính năng 1 dòng)"},
        "is_active": {"label": "Kích hoạt hiển thị trên Bảng giá"}
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True


class SubscriptionAdmin(ModelView, model=Subscription):
    name = "Đăng ký Gói"
    name_plural = "Đăng ký Gói"
    icon = "fa-solid fa-id-card"
    category = "Gói cước & Thanh toán"
    list_template = "billing/subscriptions_list.html"
    
    column_list = [
        Subscription.id,
        Subscription.user,
        Subscription.plan,
        Subscription.status,
        Subscription.starts_at,
        Subscription.ends_at,
        Subscription.created_at
    ]
    column_sortable_list = [Subscription.id, Subscription.status, Subscription.starts_at, Subscription.ends_at, Subscription.created_at]
    column_default_sort = [(Subscription.created_at, True)]

    column_labels = {
        Subscription.id: "ID",
        Subscription.user: "Người dùng",
        Subscription.plan: "Gói cước",
        Subscription.status: "Trạng thái",
        Subscription.starts_at: "Bắt đầu",
        Subscription.ends_at: "Hết hạn",
        Subscription.created_at: "Ngày đăng ký"
    }

    column_formatters = {
        Subscription.user: lambda m, a: Markup(f'<span class="fw-semibold text-dark">{m.user.name or m.user.email}</span><br><small class="text-muted">{m.user.email}</small>') if getattr(m, "user", None) else f"User #{m.user_id}",
        Subscription.plan: lambda m, a: Markup(f'<span class="badge bg-primary-soft text-primary fw-bold">{m.plan.name}</span><br><small class="text-muted">{(m.plan.token_amount or 0):,} tokens</small>') if getattr(m, "plan", None) else f"Plan #{m.plan_id}",
        Subscription.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else "warning-soft text-warning"} fw-bold">{"● Đang dùng" if m.status == "active" else m.status}</span>'),
        Subscription.starts_at: lambda m, a: m.starts_at.strftime("%d/%m/%Y") if m.starts_at else "",
        Subscription.ends_at: lambda m, a: m.ends_at.strftime("%d/%m/%Y") if m.ends_at else "",
        Subscription.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True


class PaymentAdmin(ModelView, model=Payment):
    name = "Lịch sử Thanh toán"
    name_plural = "Lịch sử Thanh toán"
    icon = "fa-solid fa-money-bill-wave"
    category = "Gói cước & Thanh toán"
    list_template = "billing/payments_list.html"
    
    column_list = [
        Payment.id,
        Payment.user,
        Payment.plan,
        Payment.amount,
        Payment.payment_method,
        Payment.status,
        Payment.transaction_reference,
        Payment.created_at
    ]
    column_sortable_list = [Payment.id, Payment.amount, Payment.status, Payment.created_at]
    column_default_sort = [(Payment.created_at, True)]

    column_labels = {
        Payment.id: "Mã GD",
        Payment.user: "Khách hàng",
        Payment.plan: "Gói cước",
        Payment.amount: "Số tiền",
        Payment.payment_method: "Phương thức",
        Payment.status: "Trạng thái",
        Payment.transaction_reference: "Mã tham chiếu",
        Payment.created_at: "Thời gian"
    }

    column_formatters = {
        Payment.user: lambda m, a: Markup(f'<span class="fw-semibold text-dark">{m.user.name or m.user.email}</span><br><small class="text-muted">{m.user.email}</small>') if getattr(m, "user", None) else f"User #{m.user_id}",
        Payment.plan: lambda m, a: Markup(f'<span class="badge bg-light text-dark border fw-medium">{m.plan.name}</span>') if getattr(m, "plan", None) else (f"Plan #{m.plan_id}" if m.plan_id else "-"),
        Payment.amount: lambda m, a: Markup(f'<span class="fw-bold text-success fs-7">{m.amount:,.0f} đ</span>') if m.amount else "0 đ",
        Payment.payment_method: lambda m, a: Markup(f'<span class="badge bg-secondary-soft text-dark"><i class="fa-regular fa-credit-card me-1"></i>{m.payment_method}</span>'),
        Payment.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status in ["success", "completed"] else "warning-soft text-warning"} fw-bold">{"● Hoàn thành" if m.status in ["success", "completed"] else m.status}</span>'),
        Payment.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True


class TokenLogAdmin(ModelView, model=TokenLog):
    name = "Nhật ký Token"
    name_plural = "Nhật ký Token"
    icon = "fa-solid fa-coins"
    category = "Gói cước & Thanh toán"
    list_template = "billing/token_logs_list.html"
    
    column_list = [
        TokenLog.id,
        TokenLog.user,
        TokenLog.amount_changed,
        TokenLog.type,
        TokenLog.description,
        TokenLog.created_at
    ]
    column_sortable_list = [TokenLog.id, TokenLog.amount_changed, TokenLog.created_at]
    column_default_sort = [(TokenLog.created_at, True)]

    column_labels = {
        TokenLog.id: "ID",
        TokenLog.user: "Người dùng",
        TokenLog.amount_changed: "Biến động",
        TokenLog.type: "Loại giao dịch",
        TokenLog.description: "Chi tiết nội dung",
        TokenLog.created_at: "Thời gian"
    }

    column_formatters = {
        TokenLog.user: lambda m, a: Markup(f'<span class="fw-semibold text-dark">{m.user.name or m.user.email}</span><br><small class="text-muted">{m.user.email}</small>') if getattr(m, "user", None) else f"User #{m.user_id}",
        TokenLog.amount_changed: lambda m, a: Markup(
            f'<span class="badge bg-{"success-soft text-success" if (m.amount_changed or 0) > 0 else "danger-soft text-danger"} fw-bold fs-7">'
            f'{"<i class=\"fa-solid fa-arrow-up me-1\"></i>+" if (m.amount_changed or 0) > 0 else "<i class=\"fa-solid fa-arrow-down me-1\"></i>"}{(m.amount_changed or 0):,} Token'
            f'</span>'
        ),
        TokenLog.type: lambda m, a: Markup(f'<span class="badge bg-primary-soft text-primary fw-medium">{m.type}</span>'),
        TokenLog.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }

    can_create = False
    can_edit = False
    can_delete = True
    can_export = True
    can_view_details = True

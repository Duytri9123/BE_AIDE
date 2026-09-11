from sqladmin import ModelView
from wtforms import PasswordField
from markupsafe import Markup
from app.models.user import User
from app.core.security import get_password_hash

class UserAdmin(ModelView, model=User):
    name = "Người dùng"
    name_plural = "Người dùng"
    icon = "fa-solid fa-users"
    category = "Quản lý Người dùng"
    list_template = "users/list.html"
    
    column_list = [User.id, User.name, User.email, User.status, User.role, User.tokens, User.created_at]
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
        User.tokens: "Tokens",
        User.created_at: "Ngày tạo",
        User.updated_at: "Cập nhật"
    }
    
    column_formatters = {
        User.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else "danger-soft text-danger"} fw-bold">{"Hoạt động" if m.status == "active" else (m.status or "Khóa")}</span>'),
        User.role: lambda m, a: Markup(f'<span class="badge bg-{"primary-soft text-primary" if m.role == "admin" else "secondary-soft text-muted"} fw-bold">{"Quản trị" if m.role == "admin" else "Người dùng"}</span>'),
        User.tokens: lambda m, a: Markup(f'<span class="text-primary fw-bold">{(m.tokens or 0):,}</span>'),
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
        "hashed_password": PasswordField
    }
    
    form_args = {
        "name": {"label": "Tên người dùng"},
        "email": {"label": "Địa chỉ Email"},
        "phone": {"label": "Số điện thoại"},
        "status": {"label": "Trạng thái"},
        "role": {"label": "Vai trò"},
        "tokens": {"label": "Số tokens"},
        "hashed_password": {"label": "Mật khẩu"}
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True
    
    page_size = 20
    page_size_options = [10, 20, 50, 100]
    
    async def on_model_change(self, data, model, is_created):
        if "hashed_password" in data and data["hashed_password"]:
            # If not already hashed, hash it
            if not str(data["hashed_password"]).startswith("$2"):
                data["hashed_password"] = get_password_hash(str(data["hashed_password"]))

    async def on_model_delete(self, model: User, request) -> None:
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


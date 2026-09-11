from sqladmin import ModelView
from markupsafe import Markup
from app.models.system_setting import SystemSetting
from app.models.notification import Notification
from app.models.page_content import PageContent
from app.models.activity_log import ActivityLog
import datetime

VN_TZ = datetime.timezone(datetime.timedelta(hours=7))

def format_vn_datetime(dt: datetime.datetime | None) -> str:
    """Chuyển đổi datetime UTC sang định dạng hiển thị giờ Việt Nam dd/mm/YYYY HH:MM."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(VN_TZ).strftime("%d/%m/%Y %H:%M")

class SystemSettingAdmin(ModelView, model=SystemSetting):
    name = "Cấu hình Hệ thống"
    name_plural = "Cấu hình Hệ thống"
    icon = "fa-solid fa-gear"
    category = "Cài đặt Hệ thống"
    list_template = "system/settings_list.html"
    
    column_list = [SystemSetting.id, SystemSetting.key, SystemSetting.value]
    column_labels = {
        SystemSetting.id: "ID",
        SystemSetting.key: "Mã tham số cấu hình",
        SystemSetting.value: "Giá trị tham số"
    }
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

class NotificationAdmin(ModelView, model=Notification):
    name = "Thông báo"
    name_plural = "Thông báo"
    icon = "fa-solid fa-bell"
    category = "Cài đặt Hệ thống"
    list_template = "system/activity_logs_list.html"
    
    column_list = [Notification.id, Notification.user_id, Notification.title, Notification.is_read, Notification.created_at]
    column_labels = {
        Notification.id: "ID",
        Notification.user_id: "Người dùng ID",
        Notification.title: "Tiêu đề thông báo",
        Notification.is_read: "Trạng thái",
        Notification.created_at: "Thời gian gửi"
    }
    column_formatters = {
        Notification.is_read: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.is_read else "warning-soft text-warning"} fw-bold">{"Đã đọc" if m.is_read else "Chưa đọc"}</span>'),
        Notification.created_at: lambda m, a: format_vn_datetime(m.created_at),
    }
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

class PageContentAdmin(ModelView, model=PageContent):
    name = "Nội dung Trang web"
    name_plural = "Nội dung Trang web"
    icon = "fa-solid fa-file-contract"
    category = "Cài đặt Hệ thống"
    list_template = "system/settings_list.html"
    
    column_list = [PageContent.id, PageContent.slug, PageContent.title, PageContent.updated_at]
    column_labels = {
        PageContent.id: "ID",
        PageContent.slug: "Đường dẫn (Slug)",
        PageContent.title: "Tiêu đề trang",
        PageContent.updated_at: "Cập nhật lúc"
    }
    column_formatters = {
        PageContent.updated_at: lambda m, a: format_vn_datetime(m.updated_at),
    }
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True

class ActivityLogAdmin(ModelView, model=ActivityLog):
    name = "Nhật ký Hoạt động"
    name_plural = "Nhật ký Hoạt động"
    icon = "fa-solid fa-clock-rotate-left"
    category = "Cài đặt Hệ thống"
    list_template = "system/activity_logs_list.html"
    
    column_list = [ActivityLog.id, ActivityLog.user_id, ActivityLog.action, ActivityLog.entity_type, ActivityLog.created_at]
    column_labels = {
        ActivityLog.id: "ID",
        ActivityLog.user_id: "Người dùng ID",
        ActivityLog.action: "Hành động thực hiện",
        ActivityLog.entity_type: "Phân hệ đối tượng",
        ActivityLog.created_at: "Thời gian ghi nhận"
    }
    column_formatters = {
        ActivityLog.action: lambda m, a: Markup(f'<span class="badge bg-info-soft text-info fw-bold">{m.action}</span>'),
        ActivityLog.created_at: lambda m, a: format_vn_datetime(m.created_at),
    }
    can_create = False
    can_edit = False
    can_delete = True
    can_export = True

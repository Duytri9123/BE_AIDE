from sqladmin import Admin
from app.admin.auth import authentication_backend
from app.admin.views.user_admin import UserAdmin
from app.admin.views.project_admin import ProjectAdmin, ProjectVersionAdmin, ProjectFileAdmin
from app.admin.views.device_admin import BrandAdmin, DeviceCategoryAdmin, DeviceSeriesAdmin, DeviceModelAdmin
from app.admin.views.ai_admin import AiProviderAdmin, AiProviderModelAdmin, AiConnectionAdmin, PromptTemplateAdmin
from app.admin.views.billing_admin import PlanAdmin, SubscriptionAdmin, PaymentAdmin, TokenLogAdmin
from app.admin.views.system_admin import SystemSettingAdmin, NotificationAdmin, PageContentAdmin, ActivityLogAdmin
from app.admin.views.session_admin import ConversationSessionAdmin, AnalysisIterationAdmin
from app.admin.views.analytics_view import AnalyticsView
from starlette.staticfiles import StaticFiles
from pathlib import Path

def create_admin(app, engine):
    # Mount static files for custom CSS
    static_path = Path(__file__).parent / "static"
    static_path.mkdir(exist_ok=True)
    app.mount("/admin/static", StaticFiles(directory=str(static_path)), name="admin_static")
    
    # Get templates directory
    templates_dir = Path(__file__).parent / "templates"
    
    admin = Admin(
        app, 
        engine, 
        title="DGP ELECTRIC Admin - Hệ Thống Bóc Tách & Báo Giá", 
        authentication_backend=authentication_backend,
        base_url="/admin",
        templates_dir=str(templates_dir),
    )
    
    # Register views
    admin.add_view(UserAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(ProjectVersionAdmin)
    admin.add_view(ProjectFileAdmin)
    
    admin.add_view(BrandAdmin)
    admin.add_view(DeviceCategoryAdmin)
    admin.add_view(DeviceSeriesAdmin)
    admin.add_view(DeviceModelAdmin)
    
    admin.add_view(AiProviderAdmin)
    admin.add_view(AiProviderModelAdmin)
    admin.add_view(AiConnectionAdmin)
    admin.add_view(PromptTemplateAdmin)
    
    admin.add_view(PlanAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(PaymentAdmin)
    admin.add_view(TokenLogAdmin)
    
    admin.add_view(SystemSettingAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(PageContentAdmin)
    admin.add_view(ActivityLogAdmin)
    
    admin.add_view(ConversationSessionAdmin)
    admin.add_view(AnalysisIterationAdmin)
    
    admin.add_view(AnalyticsView)
    
    return admin

from sqladmin import ModelView
from markupsafe import Markup
from app.models.conversation_session import ConversationSession
from app.models.analysis_iteration import AnalysisIteration

class ConversationSessionAdmin(ModelView, model=ConversationSession):
    name = "Phiên Hội thoại"
    name_plural = "Phiên Hội thoại"
    icon = "fa-solid fa-comments"
    category = "Bóc tách & Hội thoại"
    list_template = "sessions/sessions_list.html"
    
    column_list = [ConversationSession.id, ConversationSession.project_id, ConversationSession.status, ConversationSession.created_at]
    column_labels = {
        ConversationSession.id: "ID",
        ConversationSession.project_id: "Dự án ID",
        ConversationSession.status: "Trạng thái",
        ConversationSession.created_at: "Thời gian tạo"
    }
    column_formatters = {
        ConversationSession.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else "secondary-soft text-muted"} fw-bold">{"Hoạt động" if m.status == "active" else m.status}</span>'),
        ConversationSession.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    can_create = False
    can_edit = True
    can_delete = True
    can_export = True

class AnalysisIterationAdmin(ModelView, model=AnalysisIteration):
    name = "Lần Bóc tách AI"
    name_plural = "Lần Bóc tách AI"
    icon = "fa-solid fa-arrows-rotate"
    category = "Bóc tách & Hội thoại"
    list_template = "sessions/iterations_list.html"
    
    column_list = [AnalysisIteration.id, AnalysisIteration.session_id, AnalysisIteration.iteration_number, AnalysisIteration.created_at]
    column_labels = {
        AnalysisIteration.id: "ID",
        AnalysisIteration.session_id: "Phiên ID",
        AnalysisIteration.iteration_number: "Lần bóc tách",
        AnalysisIteration.created_at: "Thời gian thực hiện"
    }
    column_formatters = {
        AnalysisIteration.iteration_number: lambda m, a: Markup(f'<span class="badge bg-info-soft text-info fw-bold">Lần #{m.iteration_number}</span>'),
        AnalysisIteration.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    can_create = False
    can_edit = False
    can_delete = True
    can_export = True

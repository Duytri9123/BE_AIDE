from sqladmin import ModelView
from markupsafe import Markup
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.project_file import ProjectFile

class ProjectAdmin(ModelView, model=Project):
    name = "Dự án"
    name_plural = "Dự án"
    icon = "fa-solid fa-folder-open"
    category = "Quản lý Dự án"
    list_template = "projects/list.html"
    
    column_list = [Project.id, Project.name, Project.user_id, Project.category, Project.created_at, Project.updated_at]
    column_searchable_list = [Project.name, Project.category]
    column_sortable_list = [Project.id, Project.name, Project.created_at]
    column_default_sort = [(Project.created_at, True)]
    
    column_labels = {
        Project.id: "ID",
        Project.name: "Tên dự án",
        Project.user_id: "Người dùng ID",
        Project.category: "Phân loại",
        Project.created_at: "Ngày tạo",
        Project.updated_at: "Cập nhật"
    }
    
    column_formatters = {
        Project.category: lambda m, a: Markup(f'<span class="badge bg-info-soft text-info fw-bold">{m.category or "Mặc định"}</span>'),
        Project.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
        Project.updated_at: lambda m, a: m.updated_at.strftime("%d/%m/%Y %H:%M") if m.updated_at else "",
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True
    
    page_size = 20
    page_size_options = [10, 20, 50, 100]

class ProjectVersionAdmin(ModelView, model=ProjectVersion):
    name = "Phiên bản Dự án"
    name_plural = "Phiên bản Dự án"
    icon = "fa-solid fa-code-branch"
    category = "Quản lý Dự án"
    list_template = "projects/list.html"
    
    column_list = [ProjectVersion.id, ProjectVersion.project_id, ProjectVersion.version_number, ProjectVersion.status, ProjectVersion.created_at]
    column_sortable_list = [ProjectVersion.id, ProjectVersion.project_id, ProjectVersion.version_number]
    column_default_sort = [(ProjectVersion.created_at, True)]
    
    column_labels = {
        ProjectVersion.id: "ID",
        ProjectVersion.project_id: "Dự án ID",
        ProjectVersion.version_number: "Phiên bản",
        ProjectVersion.status: "Trạng thái",
        ProjectVersion.created_at: "Ngày tạo"
    }
    
    column_formatters = {
        ProjectVersion.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else "secondary-soft text-muted"} fw-bold">{m.status}</span>'),
        ProjectVersion.version_number: lambda m, a: Markup(f'<span class="badge bg-primary-soft text-primary fw-bold">v{m.version_number}</span>'),
        ProjectVersion.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 20

class ProjectFileAdmin(ModelView, model=ProjectFile):
    name = "Tập tin Bản vẽ"
    name_plural = "Tập tin Bản vẽ"
    icon = "fa-solid fa-file-lines"
    category = "Quản lý Dự án"
    list_template = "projects/files_list.html"
    
    column_list = [ProjectFile.id, ProjectFile.project_id, ProjectFile.filename, ProjectFile.file_type, ProjectFile.file_size, ProjectFile.created_at]
    column_searchable_list = [ProjectFile.filename]
    column_sortable_list = [ProjectFile.id, ProjectFile.file_size, ProjectFile.created_at]
    column_default_sort = [(ProjectFile.created_at, True)]
    
    column_labels = {
        ProjectFile.id: "ID",
        ProjectFile.project_id: "Dự án ID",
        ProjectFile.filename: "Tên tập tin",
        ProjectFile.file_type: "Định dạng",
        ProjectFile.file_size: "Dung lượng",
        ProjectFile.created_at: "Tải lên lúc"
    }
    
    column_formatters = {
        ProjectFile.file_size: lambda m, a: f'{m.file_size / 1024 / 1024:.2f} MB' if (m.file_size or 0) > 1024*1024 else f'{(m.file_size or 0) / 1024:.2f} KB',
        ProjectFile.file_type: lambda m, a: Markup(f'<span class="badge bg-secondary-soft text-muted fw-bold">{m.file_type or "DWG"}</span>'),
        ProjectFile.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    
    can_create = False
    can_edit = False
    can_delete = True
    can_export = True
    can_view_details = True
    page_size = 20

from sqladmin import ModelView
from markupsafe import Markup
from starlette.requests import Request
from typing import Any, Dict
from app.models.ai_provider import AiProvider
from app.models.ai_provider_model import AiProviderModel
from app.models.ai_connection import AiConnection
from app.models.prompt_template import PromptTemplate

class AiConnectionAdmin(ModelView, model=AiConnection):
    name = "Tài khoản & API Key"
    name_plural = "Quản lý API Keys & Connections"
    icon = "fa-solid fa-key"
    category = "Cấu hình AI"
    list_template = "ai/connections_list.html"
    create_template = "ai/connection_form.html"
    edit_template = "ai/connection_form.html"

    column_default_sort = [(AiConnection.priority, False)]

    column_list = [
        AiConnection.priority,
        AiConnection.provider,
        AiConnection.selected_model,
        AiConnection.name,
        AiConnection.api_key,
        AiConnection.is_active,
        AiConnection.status,
    ]
    
    column_searchable_list = [
        AiConnection.provider,
        AiConnection.selected_model,
        AiConnection.name,
        AiConnection.tag,
        AiConnection.email,
    ]
    
    column_sortable_list = [
        AiConnection.priority,
        AiConnection.id,
        AiConnection.provider,
        AiConnection.selected_model,
        AiConnection.name,
        AiConnection.is_active,
        AiConnection.status,
    ]
    
    column_labels = {
        AiConnection.priority: "Thứ tự ưu tiên (Priority)",
        AiConnection.provider: "Hãng AI (Provider)",
        AiConnection.selected_model: "Mô hình AI (Model)",
        AiConnection.name: "Tên kết nối / Ghi chú",
        AiConnection.api_key: "Khóa bí mật (API Key)",
        AiConnection.auth_type: "Loại xác thực",
        AiConnection.email: "Email tài khoản",
        AiConnection.is_active: "Kích hoạt sử dụng",
        AiConnection.status: "Trạng thái",
        AiConnection.tag: "Thẻ phân loại",
    }

    form_columns = [
        AiConnection.provider,
        AiConnection.selected_model,
        AiConnection.name,
        AiConnection.api_key,
        AiConnection.priority,
        AiConnection.auth_type,
        AiConnection.email,
        AiConnection.is_active,
        AiConnection.status,
        AiConnection.tag,
    ]

    form_args = {
        "provider": {
            "description": "Nhập mã provider: 'codex', 'google', 'openai', 'anthropic', 'deepseek', 'openrouter', 'groq', 'mistral', 'ollama', 'xai'"
        },
        "api_key": {
            "description": "Dán API Key của provider (ví dụ: sk-proj-... cho OpenAI)"
        },
        "selected_model": {
            "description": "Tên Model chỉ định (vd: ag/gemini-3.7-flash-high, gemini-3.6-flash, gpt-4o)"
        }
    }

    column_formatters = {
        AiConnection.provider: lambda m, a: Markup(f'<span class="badge bg-primary-soft text-primary text-uppercase fw-bold">{m.provider}</span>'),
        AiConnection.selected_model: lambda m, a: Markup(f'<code>{m.selected_model}</code>' if m.selected_model else '<span class="text-muted fst-italic">Mặc định (#1)</span>'),
        AiConnection.api_key: lambda m, a: Markup(f'<code>{m.api_key[:8] + "..." + m.api_key[-4:] if m.api_key and len(m.api_key) > 12 else (m.api_key or "<em>Chưa có key</em>")}</code>'),
        AiConnection.is_active: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.is_active else "secondary-soft text-muted"} fw-bold">{"Đang dùng" if m.is_active else "Tắt"}</span>'),
        AiConnection.status: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.status == "active" else "warning-soft text-warning"} fw-bold">{m.status}</span>'),
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True

    async def on_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        """Xử lý dữ liệu trước khi lưu connection: lưu base_url vào quotas và đồng bộ auth_type kiểu 9router"""
        form_data = await request.form()
        custom_base_url = form_data.get("base_url")

        quotas: Dict[str, Any] = dict(model.quotas) if isinstance(model.quotas, dict) else {}
        if custom_base_url and str(custom_base_url).strip():
            quotas["base_url"] = str(custom_base_url).strip()
            model.quotas = quotas
        elif "base_url" in quotas:
            quotas.pop("base_url", None)
            model.quotas = quotas

        # Tự động đồng bộ auth_type nếu phát hiện token đặc biệt kiểu 9router
        if model.api_key:
            key_str = model.api_key.strip()
            if key_str.startswith("1//"):
                model.auth_type = "oauth2"
            elif key_str.startswith("ya29.") or key_str.startswith("sess-"):
                model.auth_type = "bearer_token"



class AiProviderAdmin(ModelView, model=AiProvider):
    name = "Nhà cung cấp AI"
    name_plural = "Danh mục AI Providers"
    icon = "fa-solid fa-server"
    category = "Cấu hình AI"
    list_template = "ai/providers_list.html"
    
    column_list = [
        AiProvider.id,
        AiProvider.name,
        AiProvider.api_type,
        AiProvider.base_url,
        AiProvider.is_active,
        AiProvider.sort_order,
    ]

    column_searchable_list = [
        AiProvider.id,
        AiProvider.name,
        AiProvider.slug,
        AiProvider.api_type,
    ]
    
    column_sortable_list = [
        AiProvider.id,
        AiProvider.name,
        AiProvider.sort_order,
        AiProvider.is_active,
    ]
    
    column_labels = {
        AiProvider.id: "Mã Provider (ID)",
        AiProvider.name: "Tên nhà cung cấp",
        AiProvider.slug: "Đường dẫn (Slug)",
        AiProvider.api_type: "Chuẩn API (API Type)",
        AiProvider.base_url: "Địa chỉ máy chủ (Base URL)",
        AiProvider.description: "Mô tả",
        AiProvider.is_active: "Hoạt động",
        AiProvider.sort_order: "Thứ tự sắp xếp",
    }

    form_columns = [
        AiProvider.id,
        AiProvider.name,
        AiProvider.slug,
        AiProvider.api_type,
        AiProvider.base_url,
        AiProvider.description,
        AiProvider.is_active,
        AiProvider.sort_order,
    ]

    column_formatters = {
        AiProvider.is_active: lambda m, a: Markup(f'<span class="badge bg-{"success" if m.is_active else "danger"}">{"Hoạt động" if m.is_active else "Tắt"}</span>'),
        AiProvider.api_type: lambda m, a: Markup(f'<span class="badge bg-info">{m.api_type}</span>'),
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class AiProviderModelAdmin(ModelView, model=AiProviderModel):
    name = "Mô hình AI (Model)"
    name_plural = "Danh sách Model AI"
    icon = "fa-solid fa-robot"
    category = "Cấu hình AI"
    list_template = "ai/models_list.html"
    
    column_list = [
        AiProviderModel.id,
        AiProviderModel.sort_order,
        AiProviderModel.provider_id,
        AiProviderModel.model_key,
        AiProviderModel.label,
        AiProviderModel.is_active,
    ]
    column_searchable_list = [AiProviderModel.provider_id, AiProviderModel.model_key, AiProviderModel.label]
    column_sortable_list = [AiProviderModel.id, AiProviderModel.sort_order, AiProviderModel.provider_id, AiProviderModel.model_key]
    column_default_sort = [(AiProviderModel.sort_order, False), (AiProviderModel.id, False)]

    column_labels = {
        AiProviderModel.id: "ID",
        AiProviderModel.sort_order: "Thứ tự ưu tiên (Priority)",
        AiProviderModel.provider_id: "Thuộc Provider",
        AiProviderModel.model_key: "Mã Model (model_key)",
        AiProviderModel.label: "Tên hiển thị (Label)",
        AiProviderModel.is_active: "Hoạt động",
    }

    form_columns = [
        AiProviderModel.provider_id,
        AiProviderModel.model_key,
        AiProviderModel.label,
        AiProviderModel.is_active,
    ]

    column_formatters = {
        AiProviderModel.provider_id: lambda m, a: Markup(f'<span class="badge bg-primary-soft text-primary text-uppercase fw-bold">{m.provider_id}</span>'),
        AiProviderModel.is_active: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.is_active else "danger-soft text-danger"} fw-bold">{"Bật" if m.is_active else "Tắt"}</span>'),
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 100
    page_size_options = [50, 100, 200]


class PromptTemplateAdmin(ModelView, model=PromptTemplate):
    name = "Mẫu câu lệnh (Prompt)"
    name_plural = "Prompt Templates"
    icon = "fa-solid fa-terminal"
    category = "Cấu hình AI"
    
    column_list = [
        PromptTemplate.id,
        PromptTemplate.name,
        PromptTemplate.type,
        PromptTemplate.version,
        PromptTemplate.is_active,
    ]
    column_searchable_list = [PromptTemplate.name, PromptTemplate.type]
    column_sortable_list = [PromptTemplate.id, PromptTemplate.name]

    column_labels = {
        PromptTemplate.id: "ID",
        PromptTemplate.name: "Tên mẫu Prompt",
        PromptTemplate.type: "Loại Prompt",
        PromptTemplate.version: "Phiên bản",
        PromptTemplate.content: "Nội dung Prompt",
        PromptTemplate.description: "Mô tả",
        PromptTemplate.is_active: "Trạng thái",
    }

    form_columns = [
        PromptTemplate.name,
        PromptTemplate.type,
        PromptTemplate.version,
        PromptTemplate.content,
        PromptTemplate.description,
        PromptTemplate.is_active,
    ]

    column_formatters = {
        PromptTemplate.type: lambda m, a: Markup(f'<span class="badge bg-info-soft text-info fw-bold">{m.type}</span>'),
        PromptTemplate.is_active: lambda m, a: Markup(f'<span class="badge bg-{"success-soft text-success" if m.is_active else "secondary-soft text-muted"} fw-bold">{"Hoạt động" if m.is_active else "Tắt"}</span>'),
    }

    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 20

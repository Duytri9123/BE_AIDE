from sqladmin import ModelView
from markupsafe import Markup
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.device_series import DeviceSeries
from app.models.device_model import DeviceModel

class BrandAdmin(ModelView, model=Brand):
    name = "Thương hiệu"
    name_plural = "Thương hiệu"
    icon = "fa-solid fa-tag"
    category = "Thư viện Thiết bị"
    list_template = "devices/brands_list.html"
    
    column_list = [Brand.id, Brand.name, Brand.created_at]
    column_searchable_list = [Brand.name]
    column_sortable_list = [Brand.id, Brand.name]
    column_default_sort = [(Brand.name, False)]
    
    column_labels = {
        Brand.id: "ID",
        Brand.name: "Tên thương hiệu",
        Brand.created_at: "Ngày tạo"
    }
    
    column_formatters = {
        Brand.created_at: lambda m, a: m.created_at.strftime("%d/%m/%Y %H:%M") if m.created_at else "",
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 50

class DeviceCategoryAdmin(ModelView, model=DeviceCategory):
    name = "Danh mục Thiết bị"
    name_plural = "Danh mục Thiết bị"
    icon = "fa-solid fa-table-cells-large"
    category = "Thư viện Thiết bị"
    list_template = "devices/models_list.html"
    
    column_list = [DeviceCategory.id, DeviceCategory.name]
    column_searchable_list = [DeviceCategory.name]
    column_sortable_list = [DeviceCategory.id, DeviceCategory.name]
    
    column_labels = {
        DeviceCategory.id: "ID",
        DeviceCategory.name: "Tên danh mục thiết bị"
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 30

class DeviceSeriesAdmin(ModelView, model=DeviceSeries):
    name = "Dòng Thiết bị"
    name_plural = "Dòng Thiết bị"
    icon = "fa-solid fa-layer-group"
    category = "Thư viện Thiết bị"
    list_template = "devices/models_list.html"
    
    column_list = [DeviceSeries.id, DeviceSeries.brand_id, DeviceSeries.name]
    column_searchable_list = [DeviceSeries.name]
    column_sortable_list = [DeviceSeries.id, DeviceSeries.brand_id]
    
    column_labels = {
        DeviceSeries.id: "ID",
        DeviceSeries.brand_id: "Thương hiệu",
        DeviceSeries.name: "Tên dòng thiết bị (Series)"
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    page_size = 50

class DeviceModelAdmin(ModelView, model=DeviceModel):
    name = "Model Thiết bị"
    name_plural = "Model Thiết bị"
    icon = "fa-solid fa-microchip"
    category = "Thư viện Thiết bị"
    list_template = "devices/models_list.html"
    
    column_list = [
        DeviceModel.id, 
        DeviceModel.device_series_id,
        DeviceModel.sku,
        DeviceModel.name,
        DeviceModel.price,
        DeviceModel.discount_pct
    ]
    column_searchable_list = [DeviceModel.sku, DeviceModel.name]
    column_sortable_list = [DeviceModel.id, DeviceModel.sku, DeviceModel.price]
    
    column_labels = {
        DeviceModel.id: "ID",
        DeviceModel.device_series_id: "Dòng thiết bị (Series)",
        DeviceModel.sku: "Mã Model / SKU",
        DeviceModel.name: "Tên thiết bị chi tiết",
        DeviceModel.price: "Đơn giá (VND)",
        DeviceModel.discount_pct: "Chiết khấu (%)"
    }
    
    column_formatters = {
        DeviceModel.price: lambda m, a: Markup(f'<span class="badge bg-success-soft text-success fw-bold">{m.price:,.0f} đ</span>') if m.price else Markup('<span class="text-muted">Chưa có giá</span>'),
        DeviceModel.discount_pct: lambda m, a: Markup(f'<span class="badge bg-warning-soft text-warning fw-bold">-{m.discount_pct:.0f}%</span>') if m.discount_pct else Markup('<span class="text-muted">-</span>'),
    }
    
    can_create = True
    can_edit = True
    can_delete = True
    can_export = True
    can_view_details = True
    page_size = 50
    page_size_options = [25, 50, 100, 200]

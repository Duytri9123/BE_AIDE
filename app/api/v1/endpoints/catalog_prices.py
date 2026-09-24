"""
API endpoints để Admin quản lý giá thiết bị tùy chỉnh (Custom Price).
Cho phép nhập giá thủ công, sửa, xóa, tìm kiếm.
Tích hợp với web search để tra giá tham khảo trước khi nhập.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.db.session import get_db
from app.api.deps import get_current_admin_user, get_current_active_user
from app.models.user import User
from app.models.ai_connection import AiConnection
from app.services.ai.device_price_resolver import (
    CustomPriceStore,
    DevicePriceResolver,
    CadRegistryCache,
)
from app.services.device_catalog_engine import DeviceCatalogEngine

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class CustomPriceCreate(BaseModel):
    name: str = Field(..., description="Tên thiết bị")
    category: str = Field(..., description="Loại thiết bị: Relay, Timer, Meter, CT, VFD...")
    brand: str = Field("", description="Hãng sản xuất")
    price: int = Field(..., ge=0, description="Đơn giá VND")
    sku: str = Field("", description="Mã SKU / Model nếu có")
    source_note: str = Field("admin", description="Nguồn giá: admin / web / catalog")


class CustomPriceUpdate(BaseModel):
    price: int = Field(..., ge=0, description="Đơn giá VND mới")
    source_note: Optional[str] = None


class CustomPriceResponse(BaseModel):
    key: str
    name: str
    brand: str
    category: str
    price: int
    source_note: str
    updated_by: str
    updated_at: str


class WebSearchPriceRequest(BaseModel):
    name: str
    category: str
    brand: str = ""
    spec: str = ""


class ResolveDevicePriceRequest(BaseModel):
    name: str
    category: str
    brand: str = ""
    spec: str = ""
    part_number: str = ""
    in_a: Optional[float] = None
    poles: Optional[int] = None
    min_icu: Optional[float] = None
    enable_web_search: bool = True


# ─────────────────────────────────────────────
# ENDPOINTS - CUSTOM PRICE MANAGEMENT
# ─────────────────────────────────────────────

@router.get("/custom-prices", summary="Danh sách giá tùy chỉnh")
async def list_custom_prices(
    q: Optional[str] = Query(None, description="Tìm theo tên"),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Lấy danh sách tất cả giá tùy chỉnh do Admin nhập."""
    if q:
        items = CustomPriceStore.search(q)
    else:
        items = CustomPriceStore.list_all()
    return {"items": items, "total": len(items)}


@router.post("/custom-prices", summary="Thêm giá tùy chỉnh")
async def create_custom_price(
    body: CustomPriceCreate,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Nhập giá thủ công cho thiết bị chưa có trong catalog."""
    # Tạo key từ sku (nếu có) hoặc từ brand:category:name
    if body.sku.strip():
        key = body.sku.strip().lower()
    else:
        key = f"{body.brand}:{body.category}:{body.name}".lower().strip()

    entry = CustomPriceStore.set(
        key=key,
        price=body.price,
        name=body.name,
        brand=body.brand,
        category=body.category,
        source_note=body.source_note,
        admin_user=current_user.email or current_user.name or str(current_user.id),
    )
    return {"success": True, "entry": entry}


@router.put("/custom-prices/{key:path}", summary="Cập nhật giá tùy chỉnh")
async def update_custom_price(
    key: str,
    body: CustomPriceUpdate,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Cập nhật giá đã nhập."""
    existing = CustomPriceStore.get(key)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy giá cho key: {key}")

    entry = CustomPriceStore.set(
        key=key,
        price=body.price,
        name=existing.get("name", ""),
        brand=existing.get("brand", ""),
        category=existing.get("category", ""),
        source_note=body.source_note or existing.get("source_note", "admin"),
        admin_user=current_user.email or current_user.name or str(current_user.id),
    )
    return {"success": True, "entry": entry}


@router.delete("/custom-prices/{key:path}", summary="Xóa giá tùy chỉnh")
async def delete_custom_price(
    key: str,
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Xóa một mục giá tùy chỉnh."""
    deleted = CustomPriceStore.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy key: {key}")
    return {"success": True, "deleted_key": key}


# ─────────────────────────────────────────────
# ENDPOINTS - WEB SEARCH GIÁ THAM KHẢO
# ─────────────────────────────────────────────

@router.post("/custom-prices/web-search", summary="Tra giá tham khảo từ web")
async def web_search_price(
    body: WebSearchPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Tự động tra giá tham khảo từ web cho thiết bị chưa có trong catalog.
    Kết quả chỉ mang tính tham khảo, Admin cần xác nhận trước khi lưu.
    """
    # Lấy AI connections khả dụng
    result_conns = await db.execute(
        select(AiConnection).where(AiConnection.is_active == True)
    )
    ai_connections = list(result_conns.scalars().all())

    if not ai_connections:
        raise HTTPException(
            status_code=400,
            detail="Chưa có kết nối AI khả dụng để thực hiện web search. Vui lòng cấu hình AI connection trong Admin.",
        )

    web_result = await DevicePriceResolver.resolve_from_web(
        name=body.name,
        category=body.category,
        brand=body.brand,
        spec=body.spec,
        ai_connections=ai_connections,
        db=db,
    )

    if not web_result:
        return {
            "success": False,
            "price": 0,
            "note": "Không tìm thấy giá trên web. Vui lòng nhập giá thủ công.",
            "web_search_query": DevicePriceResolver._build_search_query(
                body.name, body.category, body.brand, body.spec
            ),
        }

    return {
        "success": True,
        "price": web_result.get("unit_price", 0),
        "note": web_result.get("price_note", ""),
        "web_search_query": web_result.get("web_search_query", ""),
        "web_search_answer": web_result.get("web_search_answer", ""),
        "source": "web_search",
    }


# ─────────────────────────────────────────────
# ENDPOINTS - RESOLVE THỐNG NHẤT (4 CẤP)
# ─────────────────────────────────────────────

@router.post("/catalog/resolve-price", summary="Tra giá thiết bị (4 cấp fallback)")
async def resolve_device_price(
    body: ResolveDevicePriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Tra giá thiết bị theo 4 cấp ưu tiên:
    1. Custom (Admin nhập tay)
    2. Catalog báo giá chính thức
    3. CAD Library (có block vẽ)
    4. Web Search tự động (nếu enable_web_search=true)
    """
    catalog_engine = DeviceCatalogEngine.get_instance()
    ai_connections: List[AiConnection] = []
    if body.enable_web_search:
        result_conns = await db.execute(
            select(AiConnection).where(AiConnection.is_active == True)
        )
        ai_connections = list(result_conns.scalars().all())

    result = await DevicePriceResolver.resolve(
        name=body.name,
        category=body.category,
        brand=body.brand,
        spec=body.spec,
        part_number=body.part_number,
        in_a=body.in_a,
        poles=body.poles,
        min_icu=body.min_icu,
        catalog_engine=catalog_engine,
        ai_connections=ai_connections if body.enable_web_search else None,
        db=db,
        enable_web_search=body.enable_web_search,
    )
    return result


# ─────────────────────────────────────────────
# ENDPOINTS - CAD LIBRARY BROWSE (CHO ADMIN)
# ─────────────────────────────────────────────

@router.get("/cad-registry/groups", summary="Danh mục nhóm CAD")
async def get_cad_groups(
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Lấy danh sách các nhóm thiết bị trong thư viện CAD."""
    store = CadRegistryCache._load()
    groups = {
        group: len(items)
        for group, items in store["by_group"].items()
    }
    return {"groups": groups, "total_devices": len(store["devices"])}


@router.get("/cad-registry/search", summary="Tìm block CAD")
async def search_cad_blocks(
    q: str = Query(..., description="Từ khóa tìm kiếm"),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Tìm khối CAD trong thư viện theo từ khóa."""
    result = CadRegistryCache.search(q)
    if not result:
        return {"found": False, "device": None}
    return {"found": True, "device": result}


@router.get("/catalog/missing-prices", summary="Thiết bị chưa có giá")
async def get_missing_prices(
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Liệt kê các loại thiết bị trong CAD library chưa có giá trong catalog.
    Dùng để Admin biết cần nhập giá thủ công hoặc web search.
    """
    catalog_engine = DeviceCatalogEngine.get_instance()
    store = CadRegistryCache._load()

    missing = []
    for group, devices in store["by_group"].items():
        from app.services.ai.device_price_resolver import CAD_GROUP_TO_CATEGORY
        category = CAD_GROUP_TO_CATEGORY.get(group, group)
        # Kiểm tra xem category này có trong catalog không
        catalog_items = catalog_engine.type_index.get(category.upper(), [])
        has_catalog = len(catalog_items) > 0

        for dev in devices[:3]:  # lấy mẫu 3 device per group
            name = dev.get("name") or ""
            custom = CustomPriceStore.get(f":{category}:{name}".lower())
            missing.append({
                "group": group,
                "category": category,
                "name": name,
                "has_catalog_price": has_catalog,
                "has_custom_price": custom is not None,
                "needs_attention": not has_catalog and not custom,
                "cad_asset_ids": dev.get("asset_ids", [])[:1],
            })

    # Sắp xếp: thiết bị cần xử lý trước
    missing.sort(key=lambda x: (not x["needs_attention"], x["group"]))
    return {
        "items": missing,
        "total": len(missing),
        "needs_attention": sum(1 for m in missing if m["needs_attention"]),
    }

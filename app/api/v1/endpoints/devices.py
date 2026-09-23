from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import joinedload
from app.db.session import get_db
from app.models.brand import Brand
from app.models.device_category import DeviceCategory
from app.models.device_series import DeviceSeries
from app.models.device_model import DeviceModel
from app.models.user_device_library import UserDeviceLibrary
from app.models.user import User
from app.api.deps import get_current_active_user
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.services.busbar_layout_service import (
    calculate_busbar_sizing,
    generate_busbar_hole_layout,
    generate_mounting_template,
    generate_device_cad_svg
)

router = APIRouter()

class BrandResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class CategoryResponse(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class DeviceSeriesResponse(BaseModel):
    id: int
    brand_id: int
    device_category_id: int
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class DeviceModelResponse(BaseModel):
    id: int
    device_series_id: int
    sku: str
    name: str
    price: float
    discount_pct: float
    dimensions: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Backward & Frontend-friendly direct attributes
    model_code: Optional[str] = None
    rated_current_a: Optional[float] = None
    breaking_capacity_ka: Optional[float] = None
    poles: Optional[int] = None
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    series_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserDeviceResponse(BaseModel):
    id: int
    brand: str
    code: str
    name: str
    spec: Optional[str]
    unit_price: Optional[float]
    
    class Config:
        from_attributes = True

class UserDeviceCreate(BaseModel):
    brand: str
    code: str
    name: str
    spec: Optional[str] = None
    unit_price: Optional[float] = None

class BusbarCalcRequest(BaseModel):
    sku: Optional[str] = None
    in_current: Optional[float] = None
    ambient_temp: float = 35.0
    ip_rating: str = "IP41"
    safety_margin: float = 1.15
    poles: Optional[int] = 3

@router.get("/brands", response_model=List[BrandResponse])
async def get_brands(db: AsyncSession = Depends(get_db)):
    """Danh sách các hãng thiết bị (LS, Schneider, Chint, ...)"""
    stmt = select(Brand).order_by(Brand.name)
    result = await db.execute(stmt)
    brands = result.scalars().all()
    return brands

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Danh sách các loại thiết bị (MCB, MCCB, ELCB, RCBO, Contactor, ...)"""
    stmt = select(DeviceCategory).order_by(DeviceCategory.name)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return categories

@router.get("/series", response_model=List[DeviceSeriesResponse])
async def get_series(
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Danh sách các dòng sản phẩm (Series)"""
    stmt = select(DeviceSeries)
    if brand_id:
        stmt = stmt.where(DeviceSeries.brand_id == brand_id)
    if category_id:
        stmt = stmt.where(DeviceSeries.device_category_id == category_id)
    stmt = stmt.order_by(DeviceSeries.name)
    result = await db.execute(stmt)
    series = result.scalars().all()
    return series

def _build_model_response(m: DeviceModel) -> DeviceModelResponse:
    params = m.parameters or {}
    series = getattr(m, "series", None)
    brand = getattr(series, "brand", None) if series else None
    category = getattr(series, "category", None) if series else None

    # Handle current rating or capacity
    in_val = params.get("in")
    if in_val is not None:
        try:
            in_val = float(in_val)
        except (ValueError, TypeError):
            in_val = None

    icu_val = params.get("icu")
    if icu_val is not None:
        try:
            icu_val = float(icu_val)
        except (ValueError, TypeError):
            icu_val = None

    p_val = params.get("p")
    if p_val is not None:
        try:
            p_val = int(p_val)
        except (ValueError, TypeError):
            p_val = None

    return DeviceModelResponse(
        id=m.id,
        device_series_id=m.device_series_id,
        sku=m.sku,
        name=m.name,
        price=m.price,
        discount_pct=m.discount_pct,
        dimensions=m.dimensions,
        parameters=m.parameters,
        model_code=m.sku,
        rated_current_a=in_val,
        breaking_capacity_ka=icu_val,
        poles=p_val,
        brand_id=series.brand_id if series else None,
        brand_name=brand.name if brand else None,
        category_id=series.device_category_id if series else None,
        category_name=category.name if category else None,
        series_name=series.name if series else None
    )

from sqlalchemy.orm import selectinload

@router.get("/models", response_model=List[DeviceModelResponse])
async def get_models(
    brand_id: Optional[int] = None,
    brand_ids: Optional[str] = None,
    category_id: Optional[int] = None,
    series_id: Optional[int] = None,
    q: Optional[str] = None,
    poles: Optional[int] = None,
    min_in: Optional[float] = None,
    max_in: Optional[float] = None,
    min_icu: Optional[float] = None,
    skip: int = 0,
    limit: int = 2000,
    db: AsyncSession = Depends(get_db)
):
    """Danh sách model thiết bị với bộ lọc nâng cao"""
    stmt = (
        select(DeviceModel)
        .options(
            selectinload(DeviceModel.series).selectinload(DeviceSeries.brand),
            selectinload(DeviceModel.series).selectinload(DeviceSeries.category)
        )
    )
    
    joined_series = False
    if brand_ids:
        b_list = [int(x.strip()) for x in brand_ids.split(",") if x.strip().isdigit()]
        if b_list:
            stmt = stmt.join(DeviceModel.series)
            stmt = stmt.where(DeviceSeries.brand_id.in_(b_list))
            joined_series = True

    if brand_id or category_id or series_id:
        if not joined_series:
            stmt = stmt.join(DeviceModel.series)
            joined_series = True
        if brand_id and not brand_ids:
            stmt = stmt.where(DeviceSeries.brand_id == brand_id)
        if category_id:
            stmt = stmt.where(DeviceSeries.device_category_id == category_id)
        if series_id:
            stmt = stmt.where(DeviceModel.device_series_id == series_id)

    if q:
        search_pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                DeviceModel.sku.ilike(search_pattern),
                DeviceModel.name.ilike(search_pattern)
            )
        )
    
    stmt = stmt.order_by(DeviceModel.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    models = result.scalars().all()

    # Filter by JSON parameters if specified (poles, in, icu)
    from app.api.v1.endpoints.cad_library import manifest, resolve_model_asset
    assets = manifest()["items"]
    filtered = []
    for m in models:
        params = m.parameters or {}
        m_p = params.get("p")
        m_in = params.get("in")
        m_icu = params.get("icu")
        
        if poles is not None and m_p != poles:
            continue
        if min_in is not None and (m_in is None or m_in < min_in):
            continue
        if max_in is not None and (m_in is None or m_in > max_in):
            continue
        if min_icu is not None and (m_icu is None or m_icu < min_icu):
            continue
        response = _build_model_response(m)
        asset = resolve_model_asset(m.sku, m.parameters, assets)
        from app.services.cad.library_taxonomy import classify
        classification = classify(m.name, response.category_name or '')
        response.parameters = {**(response.parameters or {}),
                               "library_kind": classification['kind'] if classification['kind'] != 'unclassified' or not asset else asset['kind'],
                               "library_group": classification['group'] if classification['kind'] != 'unclassified' or not asset else asset['group'],
                               "cad": {**(params.get('cad') or {}), "asset_id": asset["id"], "is_collection": asset.get('is_collection', False)} if asset else None}
        filtered.append(response)

    return filtered

@router.get("/models/{sku}", response_model=DeviceModelResponse)
async def get_model_by_sku(sku: str, db: AsyncSession = Depends(get_db)):
    """Lấy chi tiết 1 thiết bị theo mã SKU"""
    stmt = (
        select(DeviceModel)
        .where(DeviceModel.sku == sku)
        .options(
            selectinload(DeviceModel.series).selectinload(DeviceSeries.brand),
            selectinload(DeviceModel.series).selectinload(DeviceSeries.category)
        )
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy thiết bị mã '{sku}'")
    return _build_model_response(model)

@router.get("/models/{model_id}/views")
async def get_device_views(model_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.cad.device_preview import device_views
    from app.api.v1.endpoints.cad_library import render_layout_svg, resolve_model_asset, manifest, guess_view_label

    model = await db.get(DeviceModel, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    params = model.parameters or {}
    all_items = manifest()["items"]
    asset = resolve_model_asset(model.sku, params, all_items)

    if asset:
        # Lấy parent_asset_id để tìm tất cả mặt nhìn liên quan
        parent_id = asset.get("parent_asset_id") or asset["id"]

        # Gom tất cả DXF cùng parent_asset_id (hoặc chính nó nếu không có parent)
        siblings = [
            item for item in all_items
            if (item.get("parent_asset_id") or item["id"]) == parent_id
        ]

        # Nếu chỉ có 1 item (chính nó), dùng luôn
        if not siblings:
            siblings = [asset]

        # Sắp xếp: mặt đứng (ratio cao) lên trước — giống endpoint /grouped
        def _sort_key(m):
            w = m.get("width", 1) or 1
            h = m.get("height", 1) or 1
            return -(h / w)
        siblings.sort(key=_sort_key)

        views_out = []
        for item in siblings:
            w, h = item.get("width", 0) or 0, item.get("height", 0) or 0
            view_label = guess_view_label(w, h)
            # Tên tab: "Mặt đứng · MDC"  hoặc chỉ "Mặt đứng" nếu block name không có ý nghĩa
            block = item.get("source_block", "")
            tab_title = f"{view_label} · {block}" if block and not block.startswith("*") else view_label

            try:
                svg = render_layout_svg(item["id"])
            except Exception:
                svg = None

            views_out.append(dict(
                id=item["id"],
                title=tab_title,
                view_label=view_label,
                source_block=block,
                source_file=item.get("source_file", ""),
                width=w,
                height=h,
                units=item.get("units", ""),
                svg=svg,
                status="source_geometry",
            ))

        # Tìm số catalog model khác cùng dùng nhóm CAD này (same CAD, different specs)
        all_view_ids = {it["id"] for it in siblings}
        id_list = ",".join("'" + vid + "'" for vid in all_view_ids)
        from sqlalchemy import text as sa_text
        shared_res = await db.execute(
            sa_text(f"SELECT COUNT(DISTINCT id) FROM device_models "
                    f"WHERE json_extract(parameters,'$.cad.asset_id') IN ({id_list})")
        )
        shared_count = shared_res.scalar() or 1

        note = (
            f"{asset['source_block']} · {asset['source_file']} · {asset['units']}. "
            f"Hướng nhìn và model chưa được xác minh."
        )
        if shared_count > 1:
            note += f" Hình dạng CAD này áp dụng cho {shared_count} model có cùng form factor."

        return dict(
            sku=model.sku,
            source="cad_library",
            asset_id=asset["id"],
            parent_asset_id=parent_id,
            view_count=len(views_out),
            shared_models_count=shared_count,
            note=note,
            views=views_out,
        )

    if (params.get("cad") or {}).get("asset_id") or model.sku.startswith("CAD:"):
        raise HTTPException(status_code=404, detail="Liên kết CAD không còn file nguồn. Vui lòng nạp lại thư viện.")

    # Fallback: vẽ kích thước từ dimensions (không có file DXF)
    return device_views(model.sku, model.dimensions, params.get("accessory_data"))



@router.post("/busbar-calc")
async def calculate_device_busbar(
    req: BusbarCalcRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Tính toán kích thước thanh cái đồng (Busbar Sizing) và tọa độ đột lỗ 2D/3D (CAD Layout)
    """
    target_in = req.in_current
    device_model = None

    if req.sku:
        stmt = select(DeviceModel).where(DeviceModel.sku == req.sku)
        result = await db.execute(stmt)
        device_model = result.scalar_one_or_none()
        if device_model and target_in is None:
            target_in = (device_model.parameters or {}).get("in", 100)

    if target_in is None:
        target_in = 100.0

    # 1. Busbar Sizing
    sizing = calculate_busbar_sizing(
        in_current=target_in,
        ambient_temp=req.ambient_temp,
        ip_rating=req.ip_rating,
        safety_margin=req.safety_margin
    )

    # 2. Terminal & Hole Layout
    dims = device_model.dimensions if device_model else {}
    params = device_model.parameters if device_model else {}

    w = dims.get("w", 75) if dims else 75
    h = dims.get("h", 130) if dims else 130
    d = dims.get("d", 82) if dims else 82
    p = params.get("p", req.poles or 3) if params else (req.poles or 3)

    hole_layout = generate_busbar_hole_layout(
        device_width=w,
        device_height=h,
        device_depth=d,
        poles=p,
        pitch=dims.get("pitch") if dims else None,
        pole_w=dims.get("pole_w") if dims else None,
        busbar_level=dims.get("busbar_level") if dims else None,
        busbar_holes_spec=params.get("busbar_holes") if params else None
    )

    mounting = generate_mounting_template(
        device_width=w,
        device_height=h,
        mount_holes_spec=params.get("mount_holes") if params else None
    )

    svg_preview = None
    if device_model:
        svg_preview = generate_device_cad_svg({
            "sku": device_model.sku,
            "name": device_model.name,
            "dimensions": dims,
            "parameters": params
        })

    return {
        "sku": device_model.sku if device_model else None,
        "device_name": device_model.name if device_model else None,
        "busbar_sizing": sizing,
        "terminal_hole_layout": hole_layout,
        "mounting_template": mounting,
        "svg_cad_preview": svg_preview
    }

@router.get("/user-items", response_model=List[UserDeviceResponse])
async def get_user_items(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Danh sách thiết bị của user"""
    stmt = select(UserDeviceLibrary).where(UserDeviceLibrary.user_id == current_user.id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return items

@router.post("/user-items", response_model=UserDeviceResponse)
async def create_user_item(
    device: UserDeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Thêm thiết bị vào library của user"""
    new_device = UserDeviceLibrary(
        user_id=current_user.id,
        brand=device.brand,
        code=device.code,
        name=device.name,
        spec=device.spec,
        unit_price=device.unit_price
    )
    db.add(new_device)
    await db.commit()
    await db.refresh(new_device)
    return new_device

@router.delete("/user-items/{id}")
async def delete_user_item(
    id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Xóa thiết bị khỏi library của user"""
    stmt = select(UserDeviceLibrary).where(
        UserDeviceLibrary.id == id,
        UserDeviceLibrary.user_id == current_user.id
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()
    
    return {"message": "Device deleted successfully"}

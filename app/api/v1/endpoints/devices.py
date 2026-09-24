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
from app.api.deps import get_current_active_user, get_current_admin_user
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
    catalog_revision: int = 0
    
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

    from app.services.cad.mounting_profile import mounting_profile
    from app.api.v1.endpoints.cad_library import resolve_model_asset
    asset = resolve_model_asset(m.sku, params)
    recognition = asset.get('recognition') if asset else None
    return DeviceModelResponse(
        id=m.id,
        catalog_revision=params.get('_catalog_revision', 0),
        device_series_id=m.device_series_id,
        sku=m.sku,
        name=(recognition or {}).get('name') or m.name,
        price=m.price,
        discount_pct=m.discount_pct,
        dimensions=m.dimensions,
        parameters={**params, 'mounting_profile_status': mounting_profile(m), 'recognition': recognition},
        model_code=m.sku,
        rated_current_a=in_val,
        breaking_capacity_ka=icu_val,
        poles=p_val,
        brand_id=series.brand_id if series else None,
        brand_name=recognition['brand'] if recognition else brand.name if brand else None,
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

@router.get('/browse')
async def browse_library(q: str = '', kind: str = '', group: str = '', cad: str = 'all', face: str = '', review: str = 'all',
                         brand_id: int | None = None, category_id: int | None = None, poles: int | None = None,
                         skip: int = 0, limit: int = 24, db: AsyncSession = Depends(get_db)):
    from app.api.v1.endpoints.cad_library import manifest
    from app.services.cad.library_browser import browse_rows
    from app.services.cad.library_taxonomy import normalize
    result = await db.scalars(select(DeviceModel).options(
        selectinload(DeviceModel.series).selectinload(DeviceSeries.brand),
        selectinload(DeviceModel.series).selectinload(DeviceSeries.category)).order_by(DeviceModel.id))
    rows = browse_rows(result.all(), manifest()['items'])
    def needs_review(row):
        return bool(row['family']) and not any(v['face'] != 'unknown' for v in row['family']['views'])
    folders = {}
    for row in rows:
        if review == 'identified' and needs_review(row): continue
        if review == 'pending' and not needs_review(row): continue
        if kind and row['kind'] != kind: continue
        folders[row['group']] = folders.get(row['group'], 0) + 1
    filtered = []
    for row in rows:
        family = row['family']
        if review == 'identified' and needs_review(row): continue
        if review == 'pending' and not needs_review(row): continue
        if kind and kind != row['kind']: continue
        if group and group != row['group']: continue
        if cad == 'yes' and not family: continue
        if cad == 'no' and family: continue
        if face and (not family or not any(v['face'] == face for v in family['views'])): continue
        members = [m for m in row['members'] if (not brand_id or m.series.brand_id == brand_id)
                   and (not category_id or m.series.device_category_id == category_id)
                   and (poles is None or (m.parameters or {}).get('p') == poles)]
        if q:
            query = normalize(q)
            members = [m for m in members if query in normalize(' '.join([row['name'], m.name, m.sku,
                       m.series.name, m.series.brand.name, family['brand'] if family else '']))]
        if not members: continue
        row = {**row, 'members': members, 'model': members[0]}
        filtered.append(row)
    output = []
    for row in filtered[max(0, skip):max(0, skip) + min(100, max(1, limit))]:
        response = _build_model_response(row['model']).model_dump()
        family = row['family']
        response['name'] = row['name']
        if family: response['brand_name'] = family['brand']
        # CAD source copies and orthographic views are not orderable variants.
        variants = [m for m in row['members'] if not m.sku.startswith('CAD:')] or [row['model']]
        response['parameters'] = {**(response['parameters'] or {}), 'library_kind': row['kind'],
            'library_group': row['group'], 'recognition': family['recognition'] if family else None, 'family_key': row['key'], 'variant_count': len(variants),
            'variant_ids': [m.id for m in variants],
            'variant_options': [{'id': m.id, 'name': m.name, 'sku': m.sku} for m in variants],
            'cad': {'asset_id': family['thumbnail_id'], 'views': family['views']} if family else None}
        output.append(response)
    return {'items': output, 'total': len(filtered), 'stats': {'cad_files':len({a for r in rows if r['family'] for a in r['family']['asset_ids']}), 'cad_files_total': len(manifest()['items']), 'cad_devices':sum(bool(r['family']) for r in rows), 'catalog_only':sum(not r['family'] for r in rows)}, 'folders': [{'name': k, 'count': v} for k, v in sorted(folders.items())]}


class CatalogModelUpdate(BaseModel):
    expected_revision: int = Field(ge=0)
    w: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    h: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    d: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    cad_asset_id: str | None = None
    source_note: str = Field(min_length=1, max_length=1000)


@router.patch('/model-details/{model_id}', response_model=DeviceModelResponse)
async def update_catalog_model(model_id: int, payload: CatalogModelUpdate,
                               db: AsyncSession = Depends(get_db),
                               user: User = Depends(get_current_admin_user)):
    from datetime import datetime, timezone
    from sqlalchemy import update, func
    from app.api.v1.endpoints.cad_library import manifest
    model = await db.scalar(select(DeviceModel).where(DeviceModel.id == model_id).options(
        selectinload(DeviceModel.series).selectinload(DeviceSeries.brand),
        selectinload(DeviceModel.series).selectinload(DeviceSeries.category)))
    if model is None: raise HTTPException(404, 'Không tìm thấy thiết bị')
    params = dict(model.parameters or {})
    if params.get('_catalog_revision', 0) != payload.expected_revision:
        raise HTTPException(409, 'Catalog đã được cập nhật. Mở lại thiết bị trước khi lưu.')
    dimensions = {**(model.dimensions or {}), 'w': payload.w, 'h': payload.h, 'd': payload.d}
    if payload.cad_asset_id:
        asset = next((a for a in manifest()['items'] if a['id'] == payload.cad_asset_id), None)
        if not asset or asset.get('is_collection'):
            raise HTTPException(422, 'Chọn mã hình CAD đơn lẻ có trong thư viện.')
        params['cad'] = {'asset_id': asset['id']}
    elif model.sku.startswith('CAD:'):
        raise HTTPException(422, 'Mục nguồn CAD phải giữ liên kết hình nguồn.')
    else:
        params['cad'] = None
    params['_catalog_revision'] = payload.expected_revision + 1
    params['_catalog_edit'] = {'user_id': user.id, 'at': datetime.now(timezone.utc).isoformat(),
                               'source_note': payload.source_note.strip()}
    if not params['_catalog_edit']['source_note']:
        raise HTTPException(422, 'Nhập nguồn đối chiếu hoặc ghi chú cập nhật.')
    params['_verified'] = False
    revision = func.coalesce(DeviceModel.parameters['_catalog_revision'].as_integer(), 0)
    result = await db.execute(update(DeviceModel).where(DeviceModel.id == model_id,
        revision == payload.expected_revision).values(dimensions=dimensions, parameters=params)
        .execution_options(synchronize_session=False))
    if result.rowcount != 1:
        await db.rollback()
        raise HTTPException(409, 'Catalog vừa thay đổi. Mở lại thiết bị trước khi lưu.')
    await db.commit()
    await db.refresh(model)
    return _build_model_response(model)


@router.get('/model-details/{model_id}')
async def model_details(model_id: int, db: AsyncSession = Depends(get_db)):
    model = await db.scalar(select(DeviceModel).where(DeviceModel.id == model_id).options(
        selectinload(DeviceModel.series).selectinload(DeviceSeries.brand),
        selectinload(DeviceModel.series).selectinload(DeviceSeries.category)))
    if model is None: raise HTTPException(404, 'Không tìm thấy thiết bị')
    return _build_model_response(model)


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
        from app.services.cad.device_families import build_families
        family = next((f for f in build_families(all_items) if asset['id'] in f['asset_ids']), None)
        specs = family['views'] if family else [{'asset_id': asset['id'], 'face': 'unknown', 'title': 'Ô bản vẽ nguồn'}]
        views = [dict(id=v['asset_id'], title=v['title'], view_label=v['title'],
                      face=v['face'], svg=render_layout_svg(v['asset_id']), status='source_geometry') for v in specs]
        return dict(sku=model.sku, source='cad_library', asset_id=views[0]['id'],
                    view_count=len(views), shared_models_count=1,
                    note=' · '.join(family['sources'] if family else [asset['source_file']]), views=views)

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

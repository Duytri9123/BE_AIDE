"""Authenticated design access, separate from Library download entitlement."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from app.api.deps import get_current_active_user
from app.api.v1.endpoints import cabinet_templates
from app.api.v1.endpoints.cad_library import catalog_tb_manifest

router=APIRouter(dependencies=[Depends(get_current_active_user)])

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User


class ProductInformationRequest(BaseModel):
    project_id: int
    category: str = Field(max_length=80)
    brand: str = Field(default='', max_length=100)
    part_number: str = Field(default='', max_length=120)
    spec: str = Field(default='', max_length=200)
    poles: int | None = Field(default=None, ge=1, le=8)
    refresh: bool = False


class DeviceDetailsRequest(ProductInformationRequest):
    name: str = Field(default='', max_length=200)
    connected_load: str = Field(default='', max_length=500)
    electrical_function: str = Field(default='', max_length=100)
    upstream_device: str = Field(default='', max_length=200)
    in_a: float | None = None
    icu_ka: float | None = None
    evidence_image: str = Field(default='', max_length=6000000)


@router.post('/device-details')
async def device_details(request: DeviceDetailsRequest, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_active_user)):
    project = (await db.execute(select(Project.id).where(Project.id == request.project_id,
        Project.user_id == user.id, Project.deleted_at.is_(None)))).scalar_one_or_none()
    if project is None:
        raise HTTPException(404, 'Dự án không tồn tại.')
    from app.models.ai_connection import AiConnection
    from app.models.conversation_session import ConversationSession
    from app.models.analysis_iteration import AnalysisIteration
    from app.services.ai.vision_analyzer import VisionAnalyzerService
    from app.services.ai.connection_pool import ConnectionPoolService
    from app.services.ai.device_details import details_prompt, parse_details
    supported = ('google', 'gemini', 'openai', 'codex', 'antigravity', 'anthropic', 'claude', 'openrouter', 'deepseek')
    connections = (await db.execute(select(AiConnection).where(AiConnection.is_active == True,
        AiConnection.status == 'active', AiConnection.provider.in_(supported))
        .order_by(AiConnection.priority))).scalars().all()
    connections = [connection for connection in connections if connection.api_key]
    if not connections:
        raise HTTPException(503, 'Chưa có kết nối AI để phân tích thiết bị.')
    requirement = (await db.execute(select(AnalysisIteration.user_message)
        .join(ConversationSession, AnalysisIteration.session_id == ConversationSession.id)
        .where(ConversationSession.project_id == request.project_id)
        .order_by(AnalysisIteration.created_at.desc()).limit(1))).scalar_one_or_none() or ''
    payload = request.model_dump(exclude={'project_id', 'refresh', 'evidence_image'})
    try:
        if request.evidence_image.startswith(('data:image/png;base64,', 'data:image/jpeg;base64,')):
            import base64, tempfile
            from pathlib import Path
            from PIL import Image
            raw = base64.b64decode(request.evidence_image.split(',', 1)[1], validate=True)
            with tempfile.TemporaryDirectory(prefix='aide-device-review-') as folder:
                path = Path(folder) / 'evidence.png'
                path.write_bytes(raw)
                with Image.open(path) as picture:
                    picture.verify()
                response, _ = await ConnectionPoolService.call_with_fallback(db=db,
                    connections=connections, call_fn=VisionAnalyzerService.analyze_image,
                    image_path=str(path), prompt=details_prompt(payload, requirement))
        else:
            response, _ = await ConnectionPoolService.call_with_fallback(db=db,
                connections=connections, call_fn=VisionAnalyzerService.analyze_text,
                prompt=details_prompt(payload, requirement))
        return parse_details(response)
    except Exception:
        raise HTTPException(502, 'Chưa phân tích được chi tiết thiết bị. Vui lòng thử lại.')


@router.post('/device-recommendations')
async def device_recommendations(request: DeviceDetailsRequest, db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_active_user)):
    project = (await db.execute(select(Project.id).where(Project.id == request.project_id,
        Project.user_id == user.id, Project.deleted_at.is_(None)))).scalar_one_or_none()
    if project is None:
        raise HTTPException(404, 'Dự án không tồn tại.')
    from app.schemas.ai import ExtractedDeviceSchema
    from app.services.ai.connection_pool import ConnectionPoolService
    from app.services.ai.web_device_recommendations import research_device_products
    device = ExtractedDeviceSchema(category=request.category, name=request.name, spec=request.spec,
        poles=request.poles, in_a=request.in_a, icu_ka=request.icu_ka)
    connections = await ConnectionPoolService.get_ordered_connections(db)
    await research_device_products([device], connections, db, preferred_brand=request.brand or None)
    return {'catalog_candidates': device.catalog_candidates or {}, 'web_research': device.web_research}


@router.post('/manufacturer-information')
async def manufacturer_information(request: ProductInformationRequest,
        db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    project = (await db.execute(select(Project.id).where(Project.id == request.project_id,
        Project.user_id == user.id, Project.deleted_at.is_(None)))).scalar_one_or_none()
    if project is None: raise HTTPException(404, 'Dự án không tồn tại.')
    from app.models.ai_connection import AiConnection
    from app.models.ai_provider import AiProvider
    from app.services.ai.web_search_service import WebSearchService
    from app.services.ai.manufacturer_information import product_information, MANUFACTURER_DOMAINS
    from app.services.device_catalog_engine import catalog_engine
    supported = ('google','gemini','openai','codex','antigravity','tavily','serper','brave','brave-search')
    connection = (await db.execute(select(AiConnection).where(AiConnection.is_active == True,
        AiConnection.status == 'active', AiConnection.provider.in_(supported))
        .order_by(AiConnection.priority))).scalars().first()
    search = None
    # Send product identifiers only; never send source filenames or project documents.
    if connection and connection.api_key and (request.part_number.strip() or request.spec.strip()):
        provider = (await db.execute(select(AiProvider).where(AiProvider.id == connection.provider))).scalar_one_or_none()
        brand = '' if request.brand.lower().strip() == 'asian' else request.brand
        domains = MANUFACTURER_DOMAINS.get(brand.lower(), ())
        sites = ' OR '.join('site:'+d for d in domains)
        query = (f'{brand} {request.part_number} {request.category} official datasheet {request.spec} '
                 f'{"("+sites+")" if sites else ""}. '
                 'Trả lời ngắn bằng tiếng Việt, ghi nguồn nhà sản xuất; chưa có nguồn thì nói chưa xác minh. '
                 'Không suy model từ sản phẩm tương tự.')
        search = await WebSearchService.search(query, connection.provider, connection.api_key,
            model=connection.selected_model, max_results=3, base_url=provider.base_url if provider else None,
            refresh=request.refresh)
    return product_information(request.model_dump(), catalog_engine, search)


@router.get('/cad-candidates')
def cad_candidates():
    items,_=catalog_tb_manifest()
    safe=[]
    for item in items:
        views=[{key:view[key] for key in ('id','face','is_primary','placement') if key in view}
               for view in item.get('views',[]) if view.get('face') in ('Mặt trước','Mặt có các lỗ đấu nối')]
        if views:
            safe.append({**{key:item[key] for key in ('id','name','brand','ai_identification') if key in item},'views':views})
    return {'items':safe,'total':len(safe)}


router.add_api_route('/cabinet-templates',cabinet_templates.list_templates,methods=['GET'])
router.add_api_route('/cabinet-templates/catalog',cabinet_templates.list_template_catalog,methods=['GET'])
router.add_api_route('/cabinet-templates/separation-forms',cabinet_templates.list_separation_forms,methods=['GET'])
router.add_api_route('/cabinet-templates/generate',cabinet_templates.generate_template,methods=['POST'])
router.add_api_route('/cabinet-templates/{template_id}/preview',cabinet_templates.template_preview,methods=['GET'])


@router.get('/cabinet-templates/{template_id}/preview-cad')
def preview_cad(template_id:str):
    try:
        item = cabinet_templates.library.resolve(template_id)
        if item.get('dimensions'):
            content = cabinet_templates.library.generate(template_id, item['dimensions'])
            return Response(content, media_type='application/dxf', headers={'Cache-Control':'private, no-store'})
        path=cabinet_templates.library.source_path(item)
        return FileResponse(path,media_type='application/dxf',content_disposition_type='inline',
                            headers={'Cache-Control':'private, no-store'})
    except ValueError as exc:
        raise HTTPException(404,str(exc)) from exc


@router.get('/cabinet-templates/{template_id}/preview-3d')
def preview_cabinet_3d(template_id: str,
        height: float | None = Query(default=None, gt=100, le=10000, allow_inf_nan=False),
        width: float | None = Query(default=None, gt=100, le=10000, allow_inf_nan=False),
        depth: float | None = Query(default=None, gt=100, le=10000, allow_inf_nan=False)):
    return cabinet_templates.preview_3d(template_id, height, width, depth)


@router.get('/cabinet-templates/{template_id}/mechanics')
def cabinet_mechanics(template_id: str):
    from app.services.cad.cabinet_source_supports import source_supports
    try:
        return source_supports(template_id)
    except (ValueError, OSError, KeyError, StopIteration):
        return {'items': [], 'provenance': {}, 'warnings': ['Chưa có dữ liệu đố gốc cho mẫu này. Có thể thêm đố theo thiết bị.']}


class CabinetAgentRequest(BaseModel):
    project_id: int
    message: str = Field(min_length=1, max_length=1500)
    cabinet_name: str = Field(default='', max_length=120)
    template: dict | None = None
    placed_devices: list[dict] = Field(default_factory=list)
    history: list[dict] = Field(default_factory=list)


@router.post('/cabinet-agent/consult')
async def cabinet_agent_consult(
    payload: CabinetAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stmt = select(Project).where(
        Project.id == payload.project_id,
        Project.user_id == current_user.id,
        Project.deleted_at.is_(None)
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(404, 'Dự án không tồn tại.')

    template = payload.template or {}
    dims = template.get('dimensions') or {'height': 700, 'width': 500, 'depth': 250}
    w = float(dims.get('width', 500))
    h = float(dims.get('height', 700))
    d = float(dims.get('depth', 250))
    desc = template.get('description', 'Tủ điện tiêu chuẩn')

    w_plate = max(50.0, w - 80.0)
    h_plate = max(50.0, h - 100.0)
    plate_area = w_plate * h_plate

    placed = payload.placed_devices or []
    device_count = len(placed)
    total_device_area = 0.0
    collisions = []

    for i, dev in enumerate(placed):
        dw = float(dev.get('width', 0) or 0)
        dh = float(dev.get('height', 0) or 0)
        dd = float(dev.get('depth', 0) or 0)
        dx = float(dev.get('x', 0) or 0)
        dy = float(dev.get('y', 0) or 0)
        d_name = dev.get('name') or dev.get('id') or f'Thiết bị #{i+1}'
        standoff = float(dev.get('standoff', 20) or 20)
        owner = dev.get('owner', 'mounting_plate')

        total_device_area += dw * dh

        if (dd + standoff) > (d + 2.0):
            collisions.append(f"{d_name}: Vượt chiều sâu tủ ({dd + standoff:.0f}mm > {d:.0f}mm)")

        if owner == 'mounting_plate':
            if dx < 0 or (dx + dw) > (w_plate + 5.0):
                collisions.append(f"{d_name}: Tràn mép ngang tấm lắp ({dx:.0f}..{dx+dw:.0f}mm / {w_plate:.0f}mm)")
            if dy < 0 or (dy + dh) > (h_plate + 5.0):
                collisions.append(f"{d_name}: Tràn mép đứng tấm lắp ({dy:.0f}..{dy+dh:.0f}mm / {h_plate:.0f}mm)")

        for j in range(i + 1, len(placed)):
            other = placed[j]
            if other.get('owner', 'mounting_plate') != owner:
                continue
            ox = float(other.get('x', 0) or 0)
            oy = float(other.get('y', 0) or 0)
            ow = float(other.get('width', 0) or 0)
            oh = float(other.get('height', 0) or 0)
            o_name = other.get('name') or other.get('id') or f'Thiết bị #{j+1}'

            if dx < (ox + ow - 2) and (dx + dw) > (ox + 2) and dy < (oy + oh - 2) and (dy + dh) > (oy + 2):
                collisions.append(f"Va chạm: {d_name} ↔ {o_name}")

    fill_ratio = round((total_device_area / plate_area) * 100, 1) if plate_area > 0 else 0.0

    msg_lower = payload.message.lower()
    from app.services.device_catalog_browser import customer_catalog_page, build_catalog_page, load_catalog_items, load_supplier_items, load_web_offers
    from app.services.ai.device_price_resolver import CustomPriceStore

    suggested_devices = []
    search_terms = []
    for kw in ['mcb', 'mccb', 'acb', 'contactor', 'relay', 'rơ le', 'biến tần', 'vfd', 'ats', 'chống sét', 'spd', 'đồng hồ']:
        if kw in msg_lower:
            search_terms.append(kw)
    for brand_kw in ['schneider', 'abb', 'mitsubishi', 'ls', 'chint', 'panasonic', 'siemens', 'fuji']:
        if brand_kw in msg_lower:
            search_terms.append(brand_kw)

    query_term = ' '.join(search_terms) if search_terms else ('mcb' if 'thiết bị' in msg_lower or 'nhỏ hơn' in msg_lower else payload.message[:30])

    try:
        catalog_res = customer_catalog_page(build_catalog_page(
            [], CustomPriceStore.list_all(),
            web_offers=load_web_offers(),
            supplier_items=load_supplier_items(),
            catalog_items=load_catalog_items(),
            documents=[],
            library_links={},
            q=query_term,
            limit=8
        ))
        items = catalog_res.get('items', [])
        for it in items[:6]:
            it_name = it.get('sku') or it.get('item_name') or it.get('name', 'Thiết bị')
            it_brand = it.get('brand') or 'Tiêu chuẩn'
            it_price = it.get('price') or 0
            spec = it.get('spec') or it.get('description') or ''
            dw = float(it.get('width') or (54.0 if 'mcb' in it_name.lower() else (105.0 if 'mccb' in it_name.lower() else 75.0)))
            dh = float(it.get('height') or (85.0 if 'mcb' in it_name.lower() else (165.0 if 'mccb' in it_name.lower() else 90.0)))
            dd = float(it.get('depth') or (70.0 if 'mcb' in it_name.lower() else (86.0 if 'mccb' in it_name.lower() else 65.0)))
            suggested_devices.append({
                'id': str(it.get('id', '')),
                'name': it_name,
                'brand': it_brand,
                'spec': spec,
                'price': it_price,
                'width': dw,
                'height': dh,
                'depth': dd,
                'reason': f"Phù hợp kích thước tủ {w:.0f}×{h:.0f}mm · {it_brand}"
            })
    except Exception:
        pass

    action_type = None
    actions = []
    if any(k in msg_lower for k in ['vào giữa', 'căn giữa', 'ra giữa', 'giữa cánh']):
        action_type = 'center_door'
        lights = [d['id'] for d in placed if any(w in str(d.get('name', '') + d.get('id', '')).lower() for w in ['đèn', 'hl', 'pilot', 'light'])]
        target_ids = lights if lights else [d['id'] for d in placed]
        if target_ids:
            actions = [{'action': 'center-door', 'ids': target_ids, 'gap': 30}]
    elif any(k in msg_lower for k in ['đèn báo pha', 'đèn pha', '3 đèn báo', 'đèn báo']):
        action_type = 'add_phase_lights'
    elif any(k in msg_lower for k in ['đồng hồ', 'vôn kế', 'ampe kế', 'volt', 'ampe']):
        action_type = 'add_meter'
    elif any(k in msg_lower for k in ['sắp xếp', 'căn chỉnh', 'thẳng hàng', 'auto arrange']):
        action_type = 'auto_arrange'
        if placed:
            actions = [{'action': 'arrange-group', 'ids': [d['id'] for d in placed], 'gap': 15}]
    elif any(k in msg_lower for k in ['xoay thiết bị', 'xoay 90', 'xoay']):
        action_type = 'rotate_device'
        if placed:
            actions = [{'action': 'rotate-group', 'ids': [d['id'] for d in placed], 'rotation': 90}]
    elif any(k in msg_lower for k in ['xóa thiết bị', 'bỏ thiết bị']):
        action_type = 'remove_device'

    llm_reply = None
    try:
        import asyncio
        import json
        from app.services.ai.connection_pool import ConnectionPoolService
        from app.services.ai.vision_analyzer import VisionAnalyzerService
        connections = await ConnectionPoolService.get_ordered_connections(db)
        if connections:
            if action_type == 'add_phase_lights':
                prompt = f"""Bạn là Kỹ sư Trưởng Thiết kế Tủ Điện AIDE (Cabinet Design AI Agent).
Người dùng vừa ra lệnh: "{payload.message}".
Hệ thống đã THỰC HIỆN NGAY: Tự động bố trí 3 Đèn Báo Pha (HL1 - Đỏ / Pha L1, HL2 - Vàng / Pha L2, HL3 - Xanh / Pha L3) lên cánh tủ, tạo lỗ khoét tròn Ø22 mm, căn thẳng hàng ngang tại vị trí chuẩn.

YÊU CẦU:
- Bắt đầu bằng xác nhận: "✅ **Đã thêm 3 đèn báo pha (Đỏ - Vàng - Xanh) lên cánh tủ:**"
- Liệt kê 3 đèn:
  * 🔴 **HL1 (Pha R / L1)**: Đèn đỏ, khoét lỗ Ø22 mm
  * 🟡 **HL2 (Pha S / L2)**: Đèn vàng, khoét lỗ Ø22 mm
  * 🟢 **HL3 (Pha T / L3)**: Đèn xanh, khoét lỗ Ø22 mm
- Xác nhận vị trí đã được căn thẳng hàng và mở lỗ khoét trên cánh tủ.
- TUYỆT ĐỐI KHÔNG thuyết trình lý thuyết hay hướng dẫn thao tác thủ công, chỉ trả lời 3-4 dòng ngắn gọn."""
            elif action_type == 'add_meter':
                prompt = f"""Bạn là Kỹ sư Trưởng Thiết kế Tủ Điện AIDE.
Người dùng vừa ra lệnh: "{payload.message}".
Hệ thống đã THỰC HIỆN NGAY: Bổ sung đồng hồ đo Volt/Ampe kích thước 72×72 mm lên cánh tủ, mở lỗ khoét vuông 68×68 mm.
Trả lời ngắn gọn (dưới 4 dòng) xác nhận đồng hồ đã được gắn lên cánh tủ."""
            elif action_type == 'auto_arrange':
                prompt = f"""Bạn là Kỹ sư Trưởng Thiết kế Tủ Điện AIDE.
Người dùng vừa ra lệnh: "{payload.message}".
Hệ thống đã THỰC HIỆN NGAY: Tự động căn chỉnh và sắp xếp lại các thiết bị trên tấm lắp thẳng hàng, đảm bảo khoảng cách an toàn và khe đi máng dây theo chuẩn IEC 61439.
Trả lời ngắn gọn (dưới 4 dòng) xác nhận đã căn chỉnh xong."""
            else:
                prompt = f"""Bạn là Kỹ sư Trưởng Thiết kế Tủ Điện AIDE (Cabinet Design AI Agent).
Nhiệm vụ: Phân tích nhanh bố trí tủ điện 2D/3D và hỗ trợ kỹ sư điều chỉnh thiết bị.

THÔNG TIN TỦ ĐIỆN HIỆN TẠI:
- Kích thước vỏ tủ: W={w}mm × H={h}mm × D={d}mm ({desc})
- Kích thước tấm lắp: {w_plate}mm × {h_plate}mm
- Số lượng thiết bị: {device_count} cái | Tỷ lệ chiếm dụng (Fill Ratio): {fill_ratio}%
- Cảnh báo va chạm / tràn mép: {', '.join(collisions) if collisions else 'Không phát hiện va chạm nào'}

YÊU CẦU CỦA KỸ SƯ:
"{payload.message}"

HƯỚNG DẪN TRẢ LỜI:
- Trả lời đúng trọng tâm câu hỏi hoặc yêu cầu điều chỉnh.
- Trả lời ngắn gọn, thực tế, súc tích (dưới 5-7 dòng). Tuyệt đối không viết văn chương dài dòng lý thuyết.
- Không dùng ký hiệu LaTeX math $...$, dùng số tự nhiên và đơn vị mm."""
            raw, _ = await asyncio.wait_for(
                ConnectionPoolService.call_with_fallback(
                    db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_text, prompt=prompt
                ),
                timeout=25
            )
            if raw and len(raw.strip()) > 30:
                llm_reply = raw.strip()
    except Exception:
        pass

    if not llm_reply:
        if action_type == 'center_door':
            llm_reply = "✅ **Đã căn giữa phụ kiện cánh tủ:** Các đèn / thiết bị cánh đã được căn đều chính giữa theo phương ngang ở hàng trên theo tiêu chuẩn kỹ thuật."
        elif action_type == 'add_phase_lights':
            llm_reply = """✅ **Đã thêm 3 đèn báo pha (Đỏ - Vàng - Xanh) lên cánh tủ:**
- 🔴 **HL1 (Pha R / L1)**: Đèn đỏ, khoét lỗ tròn Ø22 mm
- 🟡 **HL2 (Pha S / L2)**: Đèn vàng, khoét lỗ tròn Ø22 mm
- 🟢 **HL3 (Pha T / L3)**: Đèn xanh, khoét lỗ tròn Ø22 mm

Các đèn đã được căn thẳng hàng ngang tại nửa trên cánh tủ và mở lỗ khoét tiêu chuẩn."""
        elif action_type == 'add_meter':
            llm_reply = "✅ **Đã thêm đồng hồ Volt/Ampe 72×72 mm lên cánh tủ:** Đã tạo lỗ khoét vuông 68×68 mm và căn giữa."
        elif action_type == 'auto_arrange':
            llm_reply = "✅ **Đã tự động căn chỉnh thiết bị:** Các thiết bị trên tấm lắp đã được gióng thẳng hàng và chừa khoảng hở máng dây theo chuẩn IEC 61439."
        else:
            status_line = "🟢 **Bố trí hợp lý & an toàn**" if not collisions and 30 <= fill_ratio <= 75 else (
                "🔴 **Phát hiện va chạm / tràn kích thước**" if collisions else "🟡 **Cần lưu ý mật độ lắp đặt**"
            )
            collision_text = "\n".join([f"- ⚠️ {c}" for c in collisions]) if collisions else "- ✅ Không có va chạm giữa các thiết bị hoặc tràn mép tấm lắp."
            density_advice = (
                f"Tỷ lệ chiếm chỗ hiện tại đạt **{fill_ratio}%**. Mật độ bố trí ở mức lý tưởng (khuyến nghị 45–70% theo IEC 61439 để đảm bảo tản nhiệt tự nhiên và dự phòng mở rộng 20%)."
                if 35 <= fill_ratio <= 70 else (
                    f"Tỷ lệ chiếm chỗ đạt **{fill_ratio}%**. Tủ còn nhiều không gian trống (dưới 35%), bạn có thể bổ sung thêm thiết bị bảo vệ, thanh cái trung tính/PE hoặc chọn form tủ kích thước nhỏ hơn để tiết kiệm chi phí."
                    if fill_ratio < 35 else
                    f"Tỷ lệ chiếm chỗ đạt **{fill_ratio}%**. Mật độ thiết bị khá dày đặc (> 70%), cần lưu ý khe hở tản nhiệt giữa các thiết bị đóng cắt (tối thiểu 10–15mm) và bố trí quạt tản nhiệt hoặc lỗ thông gió cánh tủ."
                )
            )

            llm_reply = f"""### {status_line}

**1. Phân tích không gian & kích thước vỏ tủ:**
- Vỏ tủ: **{w:.0f} × {h:.0f} × {d:.0f} mm** ({desc})
- Tấm lắp hữu dụng: **{w_plate:.0f} × {h_plate:.0f} mm**
- Số lượng thiết bị: **{device_count}** thiết bị
- Tỷ lệ diện tích chiếm dụng: **{fill_ratio}%**

**2. Đánh giá an toàn & va chạm:**
{collision_text}
- {density_advice}

**3. Đề xuất & Tìm kiếm thiết bị:**
Dưới đây là các thiết bị phù hợp trong catalog mà bạn có thể cân nhắc bổ sung hoặc thay thế. Bạn có thể bấm **"Thêm vào tủ"** trên từng thẻ gợi ý bên dưới để tự động đưa vào bản vẽ 3D."""

    return {
        'reply': llm_reply,
        'action': action_type,
        'actions': actions,
        'metrics': {
            'fill_ratio': fill_ratio,
            'device_count': device_count,
            'collisions_count': len(collisions),
            'collisions': collisions,
            'cabinet_dimensions': {'width': w, 'height': h, 'depth': d},
            'plate_dimensions': {'width': w_plate, 'height': h_plate},
            'status': 'error' if collisions else ('warning' if fill_ratio > 75 else 'optimal')
        },
        'suggested_devices': suggested_devices
    }

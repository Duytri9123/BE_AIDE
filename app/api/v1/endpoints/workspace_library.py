"""Authenticated design access, separate from Library download entitlement."""
from fastapi import APIRouter, Depends, HTTPException
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

"""Authenticated design access, separate from Library download entitlement."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.api.deps import get_current_active_user
from app.api.v1.endpoints import cabinet_templates
from app.api.v1.endpoints.cad_library import catalog_tb_manifest

router=APIRouter(dependencies=[Depends(get_current_active_user)])


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
        path=cabinet_templates.library.source_path(cabinet_templates.library.resolve(template_id))
        return FileResponse(path,media_type='application/dxf',content_disposition_type='inline',
                            headers={'Cache-Control':'private, no-store'})
    except ValueError as exc:
        raise HTTPException(404,str(exc)) from exc

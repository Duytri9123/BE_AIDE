from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from app.api.deps import get_current_active_user
from app.services.cad import curated_library as library

router=APIRouter(dependencies=[Depends(get_current_active_user)])

@router.get('')
def list_catalog():
    return library.catalog()

@router.get('/product/dxf')
def product_drawing(sku:str,manufacturer:str,face:str='front'):
    try:
        aid,path=library.product_asset(sku,manufacturer,face)
        return FileResponse(path,media_type='application/dxf',filename=aid+'.dxf')
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.get('/shell/{template_id}/dxf')
def shell_drawing(template_id:str):
    try:
        item,path=library.shell(template_id)
        return FileResponse(path,media_type='application/dxf',filename=item['form_code']+'.dxf')
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.get('/asset/{asset_id}/dxf')
def asset_drawing(asset_id:str):
    try:return FileResponse(library.asset_path(asset_id),media_type='application/dxf',filename=asset_id+'.dxf')
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

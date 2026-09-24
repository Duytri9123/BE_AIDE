from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.api.deps import get_current_active_user
from app.services.cad import cabinet_templates as library

router = APIRouter(dependencies=[Depends(get_current_active_user)])


class CabinetRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=80)
    height: float = Field(gt=100, le=10000, allow_inf_nan=False)
    width: float = Field(gt=100, le=10000, allow_inf_nan=False)
    depth: float = Field(gt=100, le=10000, allow_inf_nan=False)
    name: str = Field(default='', max_length=80)


@router.get('')
def list_templates(height: float = Query(gt=100, le=10000, allow_inf_nan=False), width: float = Query(gt=100, le=10000, allow_inf_nan=False),
                   depth: float = Query(gt=100, le=10000, allow_inf_nan=False),
                   kind: Literal['', 'indoor', 'outdoor', 'fire', 'unknown'] = ''):
    try:
        rows = library.candidates(dict(height=height, width=width, depth=depth), kind)
        return {'items': rows, 'total': len(rows)}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/generate')
def generate_template(request: CabinetRequest):
    try:
        content = library.generate(request.template_id, dict(height=request.height, width=request.width,
                                                             depth=request.depth), request.name.strip())
        return Response(content, media_type='application/dxf', headers={'X-Cabinet-Template': request.template_id})
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/{template_id}/source')
def download_source(template_id: str):
    try:
        return FileResponse(library.source_path(library.resolve(template_id)), media_type='application/dxf',
                            filename=template_id + '.dxf')
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get('/{template_id}/preview')
def template_preview(template_id: str):
    try:
        path = library.source_path(library.resolve(template_id))
        return Response(library.preview(template_id, path.stat().st_mtime_ns), media_type='image/svg+xml',
                        headers={'X-Content-Type-Options': 'nosniff'})
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

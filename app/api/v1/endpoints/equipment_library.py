"""Read-only API for the source-backed 2026 equipment catalog."""
from fastapi import APIRouter, HTTPException, Query

from app.services.equipment_library import catalog_manifest, get_equipment, search_equipment

router = APIRouter()


@router.get('/manifest')
def manifest():
    try:
        return catalog_manifest()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get('/search')
def search(q: str = '', brand: str | None = None, cad_status: str | None = None,
           limit: int = Query(20, ge=1, le=100)):
    try:
        return {'path_base': 'Tudien/CATALOG_PHU_KIEN_DOC_LAP',
                'items': search_equipment(q, brand, cad_status, limit)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get('/{catalog_id}')
def detail(catalog_id: str):
    try:
        item = get_equipment(catalog_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail='Equipment record not found')
    return item

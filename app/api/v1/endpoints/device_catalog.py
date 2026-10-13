from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_current_active_user
from app.services.device_catalog_browser import build_catalog_page, load_web_offers, load_supplier_items, load_catalog_documents
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.ai.device_price_resolver import CustomPriceStore

router = APIRouter()

@router.get('')
async def catalog(q: str='', brand: str='', category: str='', skip: int=Query(0,ge=0),
                  limit: int=Query(30,ge=1,le=100), current_user=Depends(get_current_active_user)):
    def read():
        return build_catalog_page(DeviceCatalogEngine.get_instance().items, CustomPriceStore.list_all(),
                                  web_offers=load_web_offers(),supplier_items=load_supplier_items(),documents=load_catalog_documents(),q=q,brand=brand,category=category,skip=skip,limit=limit)
    return await run_in_threadpool(read)

@router.get('/documents/{document_id}')
async def source_pricebook(document_id:str,current_user=Depends(get_current_active_user)):
    if document_id not in {'ls-2026-10-01','chint-2026'}:raise HTTPException(404,'Không tìm thấy tài liệu.')
    path=Path(__file__).resolve().parents[4]/'storage/catalog-pricebooks'/f'{document_id}.pdf'
    if not path.is_file():raise HTTPException(404,'Chưa có tài liệu nguồn trên máy chủ này.')
    return FileResponse(path,media_type='application/pdf',filename=f'Bang-gia-{document_id}.pdf')

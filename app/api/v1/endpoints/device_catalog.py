from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_current_active_user, get_current_admin_user
from app.services.device_catalog_browser import build_catalog_page, load_web_offers, load_supplier_items, load_catalog_documents, customer_catalog_page
from app.services.ai.device_price_resolver import CustomPriceStore
from app.services.pricebook_library_links import load_links, load_price_options

router = APIRouter()

@router.get('')
async def catalog(q: str='', brand: str='', category: str='', product_line: str='', equipment_catalog_id: str='', price_row_id: str='', skip: int=Query(0,ge=0),
                  limit: int=Query(30,ge=1,le=100), current_user=Depends(get_current_active_user)):
    def read():
        display_links = {}
        if equipment_catalog_id:
            from app.services.library_price_matching import device_configuration_links
            display_links = {**device_configuration_links(equipment_catalog_id), **load_price_options()}
        result=customer_catalog_page(build_catalog_page([], CustomPriceStore.list_all(),
                                  web_offers=load_web_offers(),supplier_items=load_supplier_items(),documents=load_catalog_documents(),library_links={**display_links, **load_links()},q=q,brand=brand,category=category,product_line=product_line,equipment_catalog_id=equipment_catalog_id,price_row_id=price_row_id,skip=skip,limit=limit))
        if equipment_catalog_id:
            from app.services.library_price_matching import device_price_diagnostic
            result['price_diagnostic']=device_price_diagnostic(equipment_catalog_id)
            if not result['total']:
                from app.services.catalogtb_browser import browser_data
                from app.services.ai.takeoff_pricebook import published_rows
                from app.services.library_reference_prices import reference_rows
                device=next((d for d in browser_data()['items'] if d['id']==equipment_catalog_id),None)
                references=reference_rows(device,published_rows()) if device else []
                if references:
                    # Browse documented alternatives without asserting the
                    # source CAD has their model, ratings or physical geometry.
                    result=customer_catalog_page(build_catalog_page([],[],supplier_items=[{**r,'currency':'VND'} for r in references],
                        q=q,brand=brand,category=category,product_line=product_line,price_row_id=price_row_id,skip=skip,limit=limit))
                    result['price_diagnostic']={'status':'catalog_reference_prices','message':'Giá các mã trong catalog tham khảo dưới đây. Chọn mã, hãng và thông số theo từng dòng; đây chưa phải mã hoặc giá đã xác nhận cho CAD nguồn.'}
        return result
    return await run_in_threadpool(read)

@router.get('/documents/{document_id}')
async def source_pricebook(document_id:str,current_user=Depends(get_current_admin_user)):
    if document_id not in {'ls-2026-10-01','chint-2026'}:raise HTTPException(404,'Không tìm thấy tài liệu.')
    path=Path(__file__).resolve().parents[4]/'storage/catalog-pricebooks'/f'{document_id}.pdf'
    if not path.is_file():raise HTTPException(404,'Chưa có tài liệu nguồn trên máy chủ này.')
    return FileResponse(path,media_type='application/pdf',filename=f'Bang-gia-{document_id}.pdf')

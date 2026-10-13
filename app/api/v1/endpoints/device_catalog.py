from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool
from app.api.deps import get_current_active_user
from app.services.device_catalog_browser import build_catalog_page
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.ai.device_price_resolver import CustomPriceStore

router = APIRouter()

@router.get('')
async def catalog(q: str='', brand: str='', category: str='', skip: int=Query(0,ge=0),
                  limit: int=Query(30,ge=1,le=100), current_user=Depends(get_current_active_user)):
    def read():
        return build_catalog_page(DeviceCatalogEngine.get_instance().items, CustomPriceStore.list_all(),
                                  q=q,brand=brand,category=category,skip=skip,limit=limit)
    return await run_in_threadpool(read)

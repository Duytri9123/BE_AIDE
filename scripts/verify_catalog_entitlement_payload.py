"""Check real product payloads through the free-user entitlement dependency.

Runs an isolated in-process test app; never changes production user permissions.
The inventory fixture stays local and is not published.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import Depends,FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_current_active_user
from app.api.library_access import library_entitlement,require_library_access,allows_free_library_read
from app.api.v1.endpoints.equipment_library import router

def main():
    root=Path(__file__).resolve().parents[1]
    inventory=json.loads((root/'tmp/catalog-research/audit-inventory.json').read_text(encoding='utf8'))
    device=next(d for d in inventory['items'] if d['id']=='TB-88adac8683ca9439')
    app=FastAPI();app.include_router(router,prefix='/equipment-library',dependencies=[Depends(require_library_access)])
    app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=98018,role='user',is_superuser=False)
    app.dependency_overrides[library_entitlement]=lambda:{'full_access':False,'reason':'upgrade_required'}
    for item in inventory['items']:
        base='/api/v1/equipment-library/'+item['id']
        assert allows_free_library_read('GET',base+'/catalog-information')
        assert not allows_free_library_read('GET',base+'/dxf')
        assert not allows_free_library_read('GET',base+'/views/front/dxf')
    result={'inventory_access_checked':len(inventory['items'])}
    with TestClient(app) as client, patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device]}):
        for scope in ('current','same_brand','other_brands'):
            response=client.get(f'/equipment-library/{device["id"]}/catalog-information',params={'scope':scope})
            assert response.status_code==200,(scope,response.status_code)
            payload=response.json()
            assert isinstance(payload['items'],list)
            result[scope]={'status':200,'total':payload['total'],'first_page_rows':len(payload['items'])}
    print(json.dumps(result))
    (root/'docs/catalog-entitlement-payload-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()

"""Verify every imported product reaches the public pricebook without CAD matching."""
import json
from pathlib import Path
from collections import Counter
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v1.endpoints.device_catalog import router
from app.api.deps import get_current_active_user
from app.services.device_catalog_browser import (build_catalog_page,customer_catalog_page,
    load_supplier_items,load_web_offers,load_catalog_items)

def main():
    root=Path(__file__).resolve().parents[1]
    raw=build_catalog_page([],[],supplier_items=load_supplier_items(),web_offers=load_web_offers(),
                           catalog_items=load_catalog_items(),limit=100000)
    public=customer_catalog_page(raw)
    assert len(public['items'])==raw['total']
    assert len({r['id'] for r in public['items']})==len(public['items'])
    assert all(len(r['columns'])==len(r['cells']) for r in public['items'])
    assert all(not {'source_url','source_page','source_sha256','source_row'} & r.keys() for r in public['items'])
    app=FastAPI();app.include_router(router,prefix='/device-catalog')
    app.dependency_overrides[get_current_active_user]=lambda:object()
    client=TestClient(app)
    report=[]
    for brand in ['LS Electric','CHINT','Mitsubishi Electric','Schneider Electric','Shihlin','ABB']:
        rows=[r for r in public['items'] if r['brand']==brand]
        for skip in (0,max(0,len(rows)-100)):
            response=client.get('/device-catalog',params={'brand':brand,'skip':skip,'limit':100})
            assert response.status_code==200,response.text
            body=response.json()
            assert body['total']==len(rows),(brand,body['total'],len(rows))
            assert [r['id'] for r in body['items']]==[r['id'] for r in rows[skip:skip+100]]
        report.append({'brand':brand,'products':len(rows),'priced':sum(r['price'] is not None for r in rows),
                       'without_price':sum(r['price'] is None for r in rows),'api_first_last_pages':'passed'})
    target=root/'tmp/priority-pricebooks/public-feed.json'
    target.write_text(json.dumps(public,ensure_ascii=False),encoding='utf8')
    report={'products':raw['total'],'without_price':sum(r['price'] is None for r in public['items']),
            'all_imported_rows_serialized':True,'cad_required':False,'manufacturers':report}
    (root/'docs/pricebook-feed-check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report))

if __name__=='__main__':main()

import json
import unittest
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_current_active_user
from app.api.v1.endpoints.device_catalog import router
from app.services.device_catalog_browser import customer_catalog_page, build_catalog_page, load_supplier_items
from app.services.ai.manufacturer_registry import manufacturer_categories


class CustomerPricebookPrivacyTests(unittest.TestCase):
    def test_nested_response_contains_no_sourcing_information(self):
        row = {'id':'supplier-secret','sku':'MODEL','item_name':'MODEL','brand':'LS',
               'category':'MCB','price':100,'currency':'VND','checked_at':'2026-10-13',
               'source_url':'https://private-supplier.example/price.pdf','source_label':'Secret supplier',
               'source_kind':'supplier_pricebook','source_page':123,'price_note':'Secret supplier'}
        public = customer_catalog_page(build_catalog_page([],[],supplier_items=[row],
                      documents=[{'brand':'LS','url':row['source_url']}]))
        encoded = json.dumps(public)
        for private in ('https://','source_url','source_label','source_kind','source_page',
                        'documents','Secret supplier','supplier-secret','equipment_catalog_id'):
            self.assertNotIn(private, encoded)
        self.assertEqual(public['items'][0]['price'],100)
        self.assertEqual(public['items'][0]['item_name'],'MODEL')

    def test_customer_cannot_download_source_pdf_directly(self):
        app = FastAPI();app.include_router(router,prefix='/device-catalog')
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(role='customer',is_superuser=False)
        with TestClient(app) as client:
            self.assertEqual(client.get('/device-catalog/documents/ls-2026-10-01').status_code,403)

    def test_verified_dimensions_do_not_spread_to_similar_family(self):
        rows = load_supplier_items()
        nxb = next(r for r in rows if r['item_name']=='NXB-63 3P C20 6kA')
        self.assertEqual(nxb['dimensions_mm'],{'w':54,'h':80,'d':77.8})
        nxb_h = next(r for r in rows if r['item_name']=='NXB-63H 1P C6 10kA')
        self.assertNotIn('dimensions_mm',nxb_h)
        self.assertEqual(nxb['specifications']['Icn'],'6kA')
        ls = next(r for r in rows if r['item_name']=='ABN103c')
        self.assertEqual(ls['dimensions_mm'],{'w':75,'h':130,'d':82})
        self.assertEqual(ls['specifications']['Độ sâu thân c1 (mm)'],'60')

    def test_ls_lines_filter_without_merging_manufacturer_or_prices(self):
        rows = load_supplier_items()
        regular=build_catalog_page([],[],supplier_items=rows,brand='LS',product_line='standard')
        premium=build_catalog_page([],[],supplier_items=rows,brand='LS',product_line='premium')
        self.assertGreater(regular['total'],0);self.assertGreater(premium['total'],0)
        self.assertTrue(all(r['product_line']=='standard' for r in regular['items']))
        self.assertTrue(all(r['product_line']=='premium' for r in premium['items']))
        self.assertEqual(next(r for r in rows if r['item_name']=='LA63N 1P')['product_line'],'standard')
        self.assertEqual(next(r for r in rows if r['item_name']=='LA63H 1P')['product_line'],'premium')
        self.assertTrue(all(r['brand']=='LS Electric' for r in premium['items']))

    def test_more_than_thirty_makers_have_portfolio_evidence(self):
        makers=manufacturer_categories()
        self.assertGreaterEqual(sum(bool(m['categories']) for m in makers.values()),31)
        self.assertIn('CAPACITOR',makers['Samwha']['categories'])
        self.assertIn('TIMER',makers['Crouzet']['categories'])

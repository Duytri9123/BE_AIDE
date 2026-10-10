"""Regression checks: route bypasses, paid activation, private CAD paths."""
import asyncio
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from app.api.v1.api_router import api_router
from app.api.deps import get_current_active_user
from app.api.library_access import library_entitlement
from app.db.session import get_db
from app.models import Base, Plan, Subscription, Payment
from app.services.equipment_library import DB_PATH, asset_available, get_equipment
from app.api.v1.endpoints import auth, plans, payments
from datetime import datetime, timedelta, timezone

class SecurityChecks(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(api_router, prefix='/api/v1')
        async def no_db(): yield None
        self.app.dependency_overrides[get_db] = no_db
        self.client = TestClient(self.app)
        self.user = SimpleNamespace(id=1, role='user', is_superuser=False, is_active=True)
    def test_all_library_routes_denied_before_payload(self):
        prefixes = ('equipment-library','cad-library','curated-library','cabinet-templates','device-library','catalog-prices')
        routes = [(path, methods) for path, methods in self.app.openapi()['paths'].items()
                  if any(path.startswith('/api/v1/'+p) for p in prefixes)]
        self.assertGreater(len(routes),20)
        for path, methods in routes:
            if 'get' not in methods: continue
            import re
            url = re.sub(r'\{[^}]+\}', 'not-a-real-id', path)
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code,401)
                self.app.dependency_overrides[get_current_active_user] = lambda: self.user
                self.app.dependency_overrides[library_entitlement] = lambda: {'full_access':False}
                self.assertEqual(self.client.get(url).status_code,200 if url.endswith(('/equipment-library/browse','/equipment-library/browser-data')) else 403)
                self.app.dependency_overrides.pop(get_current_active_user)
                self.app.dependency_overrides.pop(library_entitlement)
    def test_paid_browse_and_download(self):
        self.app.dependency_overrides[get_current_active_user] = lambda: self.user
        self.app.dependency_overrides[library_entitlement] = lambda: {'full_access':True}
        response = self.client.get('/api/v1/equipment-library/browse')
        self.assertEqual(response.status_code,200,response.text)
        self.assertGreaterEqual(response.json()['total'],835)
        item = response.json()['items'][0]['catalog_id']
        detail = self.client.get('/api/v1/equipment-library/'+item)
        self.assertEqual(detail.status_code,200,detail.text)
        self.assertNotIn('catalogtb/',detail.text)
        for extension in ('preview','dxf'):
            self.assertEqual(self.client.get(f'/api/v1/equipment-library/{item}/{extension}').status_code,200)
    def test_path_traversal(self):
        for path in ('catalogtb/../.env','catalogtb/C:/secret','catalogtb/index.html','catalogtb/a/CadDon/profile.json'):
            self.assertFalse(asset_available(path))

    def test_free_views_but_cannot_download(self):
        self.app.dependency_overrides[get_current_active_user] = lambda: self.user
        self.app.dependency_overrides[library_entitlement] = lambda: {'full_access':False}
        response=self.client.get('/api/v1/equipment-library/browse')
        self.assertEqual(response.status_code,200)
        cid=response.json()['items'][0]['catalog_id']
        detail=self.client.get('/api/v1/equipment-library/'+cid)
        self.assertEqual(detail.status_code,200)
        image=self.client.get(f'/api/v1/equipment-library/{cid}/preview')
        self.assertEqual(image.status_code,200)
        self.assertEqual(image.headers['content-type'],'image/png')
        self.assertTrue(image.content.startswith(b'\x89PNG'))
        view=detail.json()['cad']['views'][0]['id']
        for path in (f'{cid}/dxf',f'{cid}/dwg',f'{cid}/views/{view}/dxf',f'{cid}/views/{view}/dwg','projection-catalog','manifest','search'):
            self.assertEqual(self.client.get('/api/v1/equipment-library/'+path).status_code,403,path)
        browser=self.client.get('/api/v1/equipment-library/browser-data')
        self.assertEqual(browser.status_code,200)
        # Reviewed front/side records merge into one device without losing any source.
        import hashlib, json, re
        from urllib.parse import unquote
        from app.services.equipment_library import CATALOG_TB_ROOT
        html=(CATALOG_TB_ROOT/'index.html').read_text(encoding='utf-8')
        source=json.loads(re.search(r'<script id="catalog-data" type="application/json">(.*?)</script>',html,re.S)[1])
        expected={'TB-'+hashlib.sha1(unquote(p['json']).encode()).hexdigest()[:16] for p in source['profiles']}
        actual=set()
        for item in browser.json()['items']:
            actual.update(item.get('member_profile_ids') or [item['id']])
        self.assertEqual(actual,expected)
        self.assertEqual(browser.json()['total'],len(browser.json()['items']))
        self.assertEqual(browser.json()['view_count'],sum(len(p['single_views']) for p in source['profiles']))
        self.assertNotIn('file://',browser.text)
        self.assertNotIn('CadDon/',browser.text)
    def test_payment_proof_query(self):
        engine = create_engine('sqlite://')
        # Only the queried tables are needed; no connection to the real user DB.
        for table in (Plan.__table__, Subscription.__table__, Payment.__table__): table.create(engine)
        now=datetime.now(timezone.utc)
        with engine.begin() as conn:
            conn.execute(Plan.__table__.insert().values(id=1,name='paid',price=100,is_active=True))
            conn.execute(Subscription.__table__.insert().values(id=1,user_id=1,plan_id=1,status='active',starts_at=now-timedelta(days=1),ends_at=now+timedelta(days=1)))
            conn.execute(Payment.__table__.insert().values(id=1,user_id=1,plan_id=1,amount=100,status='completed',payment_method='Hệ thống DGP'))
        class DB:
            async def execute(_,stmt):
                with engine.connect() as conn: return conn.execute(stmt)
        async def check(expected):
            result=await library_entitlement(self.user,DB())
            self.assertEqual(result['full_access'],expected)
        asyncio.run(check(False))
        with engine.begin() as conn: conn.execute(Payment.__table__.update().values(payment_method='SePay',status='pending'))
        asyncio.run(check(False))
        with engine.begin() as conn: conn.execute(Payment.__table__.update().values(status='completed'))
        asyncio.run(check(True))
        with engine.begin() as conn: conn.execute(Subscription.__table__.update().values(ends_at=now-timedelta(seconds=1)))
        asyncio.run(check(False))
    def test_cannot_self_activate_paid(self):
        db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda:SimpleNamespace(price=100))))
        with self.assertRaises(HTTPException) as exc: asyncio.run(plans.subscribe_plan(1,self.user,db))
        self.assertEqual(exc.exception.status_code,403)
    def test_google_email_only_cannot_impersonate(self):
        with patch.object(auth.settings if hasattr(auth,'settings') else __import__('app.core.config',fromlist=['settings']).settings,'GOOGLE_CLIENT_ID','test-client'):
            with self.assertRaises(HTTPException) as exc:
                asyncio.run(auth.google_auth(auth.GoogleAuthRequest(email='admin@example.com'),None))
        self.assertEqual(exc.exception.status_code,401)

    def test_payment_simulator_denied(self):
        with self.assertRaises(HTTPException) as exc:
            asyncio.run(payments.simulate_test_payment_success(1,self.user,None))
        self.assertEqual(exc.exception.status_code,403)

    def test_webhook_without_secret_rejected(self):
        with patch.object(payments,'get_sepay_config',AsyncMock(return_value={'api_key':''})):
            with self.assertRaises(HTTPException) as exc:
                asyncio.run(payments.handle_sepay_webhook(payments.SepayWebhookPayload(),Request({'type':'http','headers':[]}),None,None))
        self.assertEqual(exc.exception.status_code,503)

    def test_production_headers_and_private_files(self):
        from app.main import app
        app.dependency_overrides[get_db] = lambda: None
        client=TestClient(app)
        try:
            for path in ('/data/CatalogTB/index.html','/.env','/@fs/E:/secret','/src/main.ts'):
                self.assertEqual(client.get(path).status_code,404)
            response=client.get('/api/v1/equipment-library/browse')
            self.assertEqual(response.status_code,401)
            self.assertEqual(response.headers['cache-control'],'private, no-store')
            self.assertEqual(client.get('/api/v1/admin-api/providers-summary').status_code,401)
        finally: app.dependency_overrides.clear()

if __name__=='__main__': unittest.main(verbosity=2)

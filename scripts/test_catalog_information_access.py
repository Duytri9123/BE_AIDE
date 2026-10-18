"""Exercise entitlement dependencies, not just direct endpoint calls."""
import unittest
from types import SimpleNamespace
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from app.api.deps import get_current_active_user
from app.api.library_access import library_entitlement, require_library_access, _requests

class CatalogInformationAccessTests(unittest.TestCase):
    def setUp(self):
        self.app=FastAPI()
        async def fixture():return {'items':[],'total':0}
        for suffix in ('catalog-information','dxf','dwg','views/front/dxf','views/front/preview'):
            self.app.add_api_route('/equipment-library/TB-0123456789abcdef/'+suffix,fixture,
                dependencies=[Depends(require_library_access)])
        self.client=TestClient(self.app)
        self.app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=98017,role='user',is_superuser=False)
        self.app.dependency_overrides[library_entitlement]=lambda:{'full_access':False,'reason':'upgrade_required'}
        _requests.pop(98017,None)
    def test_free_user_can_read_all_three_catalog_sections(self):
        for scope in ('current','same_brand','other_brands'):
            response=self.client.get('/equipment-library/TB-0123456789abcdef/catalog-information',params={'scope':scope})
            self.assertEqual(response.status_code,200)
    def test_free_user_still_cannot_download_cad(self):
        for suffix in ('dxf','dwg','views/front/dxf'):
            self.assertEqual(self.client.get('/equipment-library/TB-0123456789abcdef/'+suffix).status_code,403)
        self.assertEqual(self.client.get('/equipment-library/TB-0123456789abcdef/views/front/preview').status_code,200)
    def test_catalog_information_remains_authenticated(self):
        self.app.dependency_overrides.pop(get_current_active_user)
        self.assertEqual(self.client.get('/equipment-library/TB-0123456789abcdef/catalog-information').status_code,401)

if __name__=='__main__':unittest.main()

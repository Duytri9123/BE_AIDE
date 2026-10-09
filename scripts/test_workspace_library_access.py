import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI,Depends
from fastapi.testclient import TestClient
from app.api.deps import get_current_active_user
try:
    from app.api.library_access import require_library_access,library_entitlement
except ImportError:
    require_library_access=library_entitlement=None
from app.api.v1.endpoints.workspace_library import router as workspace_router
from app.api.v1.endpoints.cad_library import router as private_router


class WorkspaceLibraryTests(unittest.TestCase):
    def setUp(self):
        self.app=FastAPI()
        self.app.include_router(workspace_router,prefix='/analyze')
        if require_library_access:
            self.app.include_router(private_router,prefix='/cad-library',dependencies=[Depends(require_library_access)])
        self.client=TestClient(self.app)

    def login_free(self):
        self.app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=99001,role='user',is_superuser=False)
        if library_entitlement:
            self.app.dependency_overrides[library_entitlement]=lambda:dict(full_access=False,reason='upgrade_required')

    def test_free_user_can_choose_cad_without_download_manifest(self):
        self.login_free()
        item=dict(id='fixture',name='MCB',brand='LS',ai_identification={'loai_thiet_bi_code':'MCB','so_cuc':'2P'},
                  source_url='/secret',views=[dict(id='front',face='Mặt trước',is_primary=True,insert_url='/download.dxf',preview_url='/private')])
        with patch('app.api.v1.endpoints.workspace_library.catalog_tb_manifest',return_value=([item],{})):
            response=self.client.get('/analyze/cad-candidates')
        self.assertEqual(response.status_code,200)
        view=response.json()['items'][0]['views'][0]
        self.assertNotIn('insert_url',view)
        self.assertNotIn('preview_url',view)
        self.assertNotIn('source_url',response.json()['items'][0])

    @unittest.skipIf(require_library_access is None,'Separate Library entitlement policy is not installed in this checkout')
    def test_existing_library_download_guard_is_preserved(self):
        self.login_free()
        self.assertEqual(self.client.get('/cad-library/catalog-tb/view/front/insert-dxf').status_code,403)

    def test_anonymous_cannot_use_workspace_library(self):
        self.assertEqual(self.client.get('/analyze/cad-candidates').status_code,401)

    def test_workspace_has_form_preview_not_library_source_download(self):
        paths={route.path for route in workspace_router.routes}
        self.assertIn('/cabinet-templates/{template_id}/preview-cad',paths)
        self.assertNotIn('/cabinet-templates/{template_id}/source',paths)


if __name__=='__main__':unittest.main()

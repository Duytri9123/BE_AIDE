"""Run current CAD and quote services in isolated SQL state, using real geometry."""
import unittest
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.base import Base
from app.models.project import Project
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from scripts.test_layout_current_catalog import CurrentCatalogLayoutTests
import app.models


class CurrentCatalogSystemTests(unittest.IsolatedAsyncioTestCase):
    async def test_review_cad_and_pending_quote_are_saved_without_claiming_completion(self):
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                project = Project(id=990009, user_id=1, name='Current CatalogTB integration')
                db.add(project)
                await db.commit()
                devices = CurrentCatalogLayoutTests().devices()
                for device in devices:
                    device.update(panel_code='TĐT', source_filename='integration-fixture', source_page=1)
                result = await AnalysisPipelineService.generate_cad_and_quotation(
                    project, db, devices, enclosure_dimensions='1000x800x300',
                    panel_code='TĐT', per_panel=True)
                self.assertTrue(result['cad_file'])
                self.assertTrue(result['quotation_file'])
                self.assertTrue(Path(result['quotation_file']['file_path']).is_file())
                self.assertEqual(result['cad_layout']['status'], 'reference_layout_needs_review')
                self.assertFalse(result['cad_layout']['release_ready'])
                self.assertEqual(result['enclosure_spec']['source_form_review']['status'], 'needs_review')
                self.assertTrue(result['quotation_rows'])
        finally:
            await engine.dispose()


if __name__ == '__main__':
    unittest.main()

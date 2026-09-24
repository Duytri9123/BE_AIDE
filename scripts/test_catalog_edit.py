import unittest
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, Brand, DeviceCategory, DeviceSeries, DeviceModel
from app.api.v1.endpoints.devices import CatalogModelUpdate, update_catalog_model, model_details


class CatalogEditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda c: Base.metadata.create_all(c, tables=[
                Brand.__table__, DeviceCategory.__table__, DeviceSeries.__table__, DeviceModel.__table__]))
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.session.add_all([Brand(id=1, name='Test'), DeviceCategory(id=1, name='MCCB'),
            DeviceSeries(id=1, name='Test', brand_id=1, device_category_id=1),
            DeviceModel(id=1, device_series_id=1, sku='TEST', name='Test model',
                        dimensions={'w': 10, 'pitch': 5}, parameters={'in': 100})])
        await self.session.commit()

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def test_save_reload_preserves_parameters_and_rejects_stale_revision(self):
        payload = CatalogModelUpdate(expected_revision=0, w=80, h=150, d=70, source_note='Datasheet page 2')
        saved = await update_catalog_model(1, payload, self.session, SimpleNamespace(id=7))
        self.assertEqual(saved.catalog_revision, 1)
        self.assertEqual(saved.dimensions, {'w':80, 'h':150, 'd':70, 'pitch':5})
        self.assertEqual(saved.parameters['in'], 100)
        self.assertEqual(saved.parameters['_catalog_edit']['user_id'], 7)
        self.session.expire_all()
        reloaded = await model_details(1, self.session)
        self.assertEqual(reloaded.dimensions['w'], 80)
        with self.assertRaises(HTTPException) as caught:
            await update_catalog_model(1, payload, self.session, SimpleNamespace(id=7))
        self.assertEqual(caught.exception.status_code, 409)

    async def test_unknown_asset_does_not_modify_catalog(self):
        with self.assertRaises(HTTPException) as caught:
            await update_catalog_model(1, CatalogModelUpdate(expected_revision=0, cad_asset_id='missing',
                source_note='Test'), self.session, SimpleNamespace(id=7))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual((await model_details(1, self.session)).catalog_revision, 0)

    def test_invalid_dimensions(self):
        for value in (-1, 0, float('inf'), float('nan')):
            with self.assertRaises(ValidationError):
                CatalogModelUpdate(expected_revision=0, w=value, source_note='Test')


if __name__ == '__main__':
    unittest.main()

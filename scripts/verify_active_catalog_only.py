"""Regression check: retired catalogs cannot drive automatic selection."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.endpoints.cad_library import manifest as cad_manifest
from app.services.ai.device_price_resolver import CadRegistryCache, DevicePriceResolver
from app.services.device_catalog_engine import DeviceCatalogEngine
from app.services.equipment_library import catalog_manifest


async def check() -> None:
    engine = DeviceCatalogEngine.get_instance()
    assert len(engine.items) == sum(catalog_manifest()['price_rows_by_brand'].values())
    assert not engine.accessories
    assert engine.get_by_sku('LA63N') is None
    assert engine.filter_devices(brand='LS', device_type='MCB', poles=2, in_current=16) == []
    assert engine.match_from_text('MCB LS 2P 16A') == []
    assert CadRegistryCache._load()['devices'] == []
    assert all(row['cad_status'] == 'exact_model_cad' for row in cad_manifest()['items'])

    known = await DevicePriceResolver.resolve(
        name='AE1000-SW', category='ACB', brand='Mitsubishi',
        part_number='160101A00004U', catalog_engine=engine)
    unknown = await DevicePriceResolver.resolve(
        name='LA63N', category='MCB', brand='LS', part_number='LA63N',
        catalog_engine=engine, enable_web_search=True)
    assert (known['price_source'], known['unit_price']) == ('source_backed_catalog_2026', 68502000)
    assert (unknown['price_source'], unknown['unit_price']) == ('not_found', 0)
    print('Verified: only uniquely identified 2026 PDF rows can set automatic prices or insert CAD.')


if __name__ == '__main__':
    asyncio.run(check())

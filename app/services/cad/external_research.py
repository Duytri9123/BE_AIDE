"""Discover supplier drawings during design, never during source takeoff.

Discovery is not dimension approval: retain provenance and retry selection after
the supplier geometry has been imported and its units/views checked.
"""
import asyncio
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import httpx
from sqlalchemy import select
from app.models.ai_connection import AiConnection
from app.models.ai_provider import AiProvider
from app.services.ai.web_search_service import WebSearchService
from app.services.ai.manufacturer_information import product_information, MANUFACTURER_DOMAINS
from app.services.device_catalog_engine import DeviceCatalogEngine


async def acquire_supplier_dxf(source, brand):
    """Keep supplier vectors for import; never infer mm or a view from a filename."""
    domains = MANUFACTURER_DOMAINS.get(str(brand or '').lower(), ())
    url = source.get('url', '')
    def permitted(value):
        parsed = urlparse(value)
        return parsed.scheme == 'https' and any(parsed.hostname == d or
            str(parsed.hostname or '').endswith('.' + d) for d in domains)
    if not permitted(url) or not urlparse(url).path.lower().endswith('.dxf'):
        return None
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for _ in range(4):
            async with client.stream('GET', url) as response:
                if response.is_redirect:
                    from urllib.parse import urljoin
                    url = urljoin(url, response.headers.get('location', ''))
                    if not permitted(url):
                        return None
                    continue
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 10 * 1024 * 1024:
                        raise ValueError('Supplier drawing exceeds import limit')
                break
        else:
            return None
    digest = hashlib.sha256(content).hexdigest()
    folder = Path(__file__).resolve().parents[3] / 'data' / 'external_cad' / digest
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'supplier.dxf'
    path.write_bytes(content)
    import ezdxf
    from ezdxf import bbox
    doc = await asyncio.to_thread(ezdxf.readfile, path)
    errors = doc.audit().errors
    if errors:
        return {'status': 'invalid_drawing', 'source_url': url, 'sha256': digest, 'fabrication_ready': False}
    extents = await asyncio.to_thread(bbox.extents, doc.modelspace(), fast=True)
    units_mm = doc.units == 4
    return {'status': 'downloaded_requires_view_review' if units_mm else 'downloaded_requires_unit_review',
            'path': str(path), 'source_url': url, 'sha256': digest, 'units_mm': units_mm,
            'drawing_bounds': list(extents.size) if extents.has_data else None,
            'fabrication_ready': False}


def needs_external_geometry(row):
    cad = row.get('cad') or {}
    return not cad.get('asset_id') or cad.get('geometry_dimensions_status') == 'requires_depth_or_mounting_review'


async def research_missing_geometry(devices, db):
    missing = [row for row in devices if needs_external_geometry(row)]
    if not missing:
        return devices
    supported = ('google', 'gemini', 'openai', 'codex', 'antigravity', 'tavily', 'serper', 'brave', 'brave-search')
    connection = (await db.execute(select(AiConnection).where(
        AiConnection.is_active == True, AiConnection.status == 'active',
        AiConnection.provider.in_(supported)).order_by(AiConnection.priority))).scalars().first()
    provider = (await db.execute(select(AiProvider).where(
        AiProvider.id == connection.provider))).scalar_one_or_none() if connection else None
    engine = DeviceCatalogEngine.get_instance()
    semaphore = asyncio.Semaphore(3)
    grouped = {}
    for row in missing:
        key = tuple(str(row.get(k) or '') for k in ('brand', 'part_number', 'category', 'spec', 'poles'))
        grouped.setdefault(key, []).append(row)

    async def lookup(rows):
        row = rows[0]
        research = {'status': 'search_unavailable', 'sources': [], 'fabrication_ready': False}
        if connection and connection.api_key:
            sites = ' OR '.join('site:' + domain for domain in MANUFACTURER_DOMAINS.get(str(row.get('brand') or '').lower(), ()))
            # Product identifiers only; source files and project documents stay private.
            query = ' '.join(str(row.get(k) or '') for k in ('brand', 'part_number', 'category', 'spec'))
            query += (' official manufacturer CAD DWG DXF 2D dimensional drawing front side mm '
                      + sites + '. Provide source download links and exact dimensions; do not invent a model or dimensions.')
            async with semaphore:
                try:
                    result = await WebSearchService.search(query, connection.provider, connection.api_key,
                        model=connection.selected_model, max_results=5,
                        base_url=(getattr(connection, 'quotas', None) or {}).get('base_url') or (provider.base_url if provider else None))
                    info = product_information(row, engine, result)
                    research.update(status='sources_found' if info['sources'] else 'no_verified_sources',
                                    sources=info['sources'], summary=info['ai_summary'])
                    drawings = []
                    for source in info['sources']:
                        try:
                            drawing = await acquire_supplier_dxf(source, row.get('brand'))
                            if drawing:
                                drawings.append(drawing)
                        except Exception:
                            # A failed supplier download must not discard the takeoff.
                            continue
                    research['supplier_drawings'] = drawings
                except Exception:
                    research['status'] = 'search_unavailable'
        for device in rows:
            device.setdefault('cad', {})['external_research'] = dict(research)
    await asyncio.gather(*(lookup(rows) for rows in grouped.values()))
    return devices

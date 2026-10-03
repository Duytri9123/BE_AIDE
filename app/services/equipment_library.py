"""Read the source-backed equipment/CAD library for AI and API consumers."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[3] / 'Tudien' / 'CATALOG_PHU_KIEN_DOC_LAP'
SOURCE_CATALOG_DIR = SOURCE_ROOT / 'THU_VIEN_THIET_BI_AI_2026'
BACKEND_CATALOG_DIR = Path(__file__).resolve().parents[2] / 'data' / 'equipment_library_2026'
CATALOG_DIR = SOURCE_CATALOG_DIR if (SOURCE_CATALOG_DIR / 'equipment_catalog.sqlite').is_file() else BACKEND_CATALOG_DIR
DB_PATH = CATALOG_DIR / 'equipment_catalog.sqlite'


def _connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(f'Equipment catalog has not been built: {DB_PATH}')
    return sqlite3.connect(DB_PATH)


def _with_availability(item: dict[str, Any]) -> dict[str, Any]:
    # `exists` in the export describes build time; this flag describes the
    # current deployment, where the large source CAD library may be absent.
    cad = item['cad']
    for ref in (cad.get('dwg'), cad.get('dxf'), cad.get('preview')):
        if ref:
            ref['available_now'] = (SOURCE_ROOT / ref['path']).is_file()
    for view in cad['views']:
        for ref in (view.get('dxf'), view.get('preview')):
            if ref:
                ref['available_now'] = (SOURCE_ROOT / ref['path']).is_file()
    return item


def get_equipment(catalog_id: str) -> dict[str, Any] | None:
    """Get one full record, including provenance and every CAD view."""
    with _connect() as db:
        row = db.execute('SELECT record_json FROM equipment WHERE catalog_id = ?', (catalog_id,)).fetchone()
    return _with_availability(json.loads(row[0])) if row else None


def search_equipment(text: str = '', brand: str | None = None,
                     cad_status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Search complete records without treating family CAD as an exact SKU match."""
    limit = max(1, min(int(limit), 100))
    terms = re.findall(r'\w+', text or '', flags=re.UNICODE)
    clauses, params = [], []
    if terms:
        clauses.append('e.catalog_id IN (SELECT catalog_id FROM equipment_fts WHERE equipment_fts MATCH ?)')
        params.append(' AND '.join('"' + term + '"' for term in terms))
    if brand:
        clauses.append('e.brand = ?')
        params.append(brand)
    if cad_status:
        clauses.append('e.cad_status = ?')
        params.append(cad_status)
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    with _connect() as db:
        rows = db.execute('SELECT e.record_json FROM equipment e' + where +
                          ' ORDER BY e.brand,e.model,e.catalog_id LIMIT ?', (*params, limit)).fetchall()
    return [_with_availability(json.loads(row[0])) for row in rows]


def catalog_manifest() -> dict[str, Any]:
    return json.loads((CATALOG_DIR / 'manifest.json').read_text(encoding='utf-8'))


def resolve_price_variant(part_number: str, brand: str | None = None,
                          poles: int | None = None, current_a: float | None = None,
                          min_icu: float | None = None) -> dict[str, Any] | None:
    """Price only a single unambiguous source row matching an explicit code.

    A family name with several price variants is intentionally unresolved.
    The CAD link is returned as evidence, never promoted to an exact SKU match.
    """
    code = (part_number or '').strip().casefold()
    if not code:
        return None
    with _connect() as db:
        rows = db.execute("SELECT record_json FROM equipment WHERE record_type = 'priced_variant' AND "
                          '(lower(model) = ? OR lower(json_extract(record_json,\'$.material_code\')) = ?)',
                          (code, code)).fetchall()
    candidates = []
    for row in rows:
        item = json.loads(row[0])
        specs = item['specifications']
        if brand and item['brand'].casefold() != brand.strip().casefold():
            continue
        if poles is not None and specs['poles'] != poles:
            continue
        if current_a is not None:
            actual = specs['current_a']
            if actual is not None and float(actual) != float(current_a):
                continue
            if actual is None:
                display = str(specs['current_display'] or '')
                values = [float(x) for x in re.findall(r'\d+(?:[.,]\d+)?', display.replace(',', '.'))]
                if float(current_a) not in values:
                    continue
        if min_icu is not None:
            try:
                if float(specs['breaking_capacity_ka']) < float(min_icu):
                    continue
            except (TypeError, ValueError):
                continue
        if item['price'] and item['price']['amount_vnd'] is not None:
            candidates.append(item)
    if len(candidates) != 1:
        return None
    return _with_availability(candidates[0])

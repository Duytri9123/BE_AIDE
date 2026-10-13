"""Explicit reviewed one-library-device to many-price-row relationships.

Never infer a CAD association from a model name or a family match.
"""
import json
from pathlib import Path
from app.services.ai.manufacturer_registry import canonical_brand

LINKS_PATH = Path(__file__).resolve().parents[1] / 'data/pricebook_library_links.json'


def validate_links(links, price_rows, library_rows, *, review_complete):
    if not review_complete:
        raise ValueError('Complete the data review before linking to the library')
    prices = {row['id']: row for row in price_rows}
    equipment = {row['catalog_id']: row for row in library_rows}
    seen = set()
    for link in links:
        price_id, equipment_id = link['price_row_id'], link['equipment_catalog_id']
        if price_id in seen:
            raise ValueError('A price row can reference only one library device')
        seen.add(price_id)
        if price_id not in prices or equipment_id not in equipment:
            raise ValueError('Unknown price row or library device')
        if canonical_brand(prices[price_id]['brand']) != canonical_brand(equipment[equipment_id]['brand']):
            raise ValueError('Manufacturer mismatch')
        if link.get('status') != 'verified' or not str(link.get('identity_evidence') or '').strip():
            raise ValueError('Exact model and configuration evidence is required')
    return links


def publish_reviewed_links(links, price_rows, library_rows, *, review_complete, path=LINKS_PATH):
    validate_links(links, price_rows, library_rows, review_complete=review_complete)
    payload = {'schema_version': 1, 'relationship': 'equipment_one_to_price_rows_many',
               'review_complete': True, 'links': links}
    path = Path(path)
    pending = path.with_suffix('.json.tmp')
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
    pending.replace(path)


def load_links(path=LINKS_PATH):
    path = Path(path)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf8'))
    if payload.get('review_complete') is not True:
        return {}
    return {link['price_row_id']: link['equipment_catalog_id'] for link in payload['links']
            if link.get('status') == 'verified'}


def equipment_for_price(price_row_id, *, links=None):
    catalog_id = (load_links() if links is None else links).get(price_row_id)
    if not catalog_id:
        return None
    from app.services.equipment_library import get_equipment
    return get_equipment(catalog_id)

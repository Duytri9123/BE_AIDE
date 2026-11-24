"""Change a maker only after verifying an electrically compatible product."""
import asyncio
import logging
from copy import deepcopy

from app.services.ai.manufacturer_registry import canonical_brand
from app.services.ai.quotation_selection import select_quotation_devices


def verified_web_product(product, brand, device):
    """Generated standard models and conditional suggestions are not evidence."""
    from app.services.ai.web_device_recommendations import public_url
    if str(device.get('category') or '').upper() in {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB'}:
        parameters = product.get('parameters') or {}
        try:
            if not all(device.get(key) and parameters.get(key) for key in ('poles', 'in_a', 'icu_ka')):
                return False
            if (float(parameters['poles']) != float(device['poles'])
                    or float(parameters['in_a']) != float(device['in_a'])
                    or float(parameters['icu_ka']) < float(device['icu_ka'])):
                return False
        except (TypeError, ValueError):
            return False
    return bool(product.get('sku') and canonical_brand(product.get('brand')) == canonical_brand(brand)
                and product.get('auto_selectable') is True and product.get('rating_complete') is True
                and not product.get('requires_confirmation') and product.get('match_kind') == 'exact'
                and public_url(product.get('technical_url')) and product.get('technical_evidence'))


def compatible_brand_replacements(devices, brand, rows=None):
    if not brand:
        return deepcopy(devices), 0
    proposals = select_quotation_devices(devices, brand, rows)
    result, changed = [], 0
    for original, proposal in zip(devices, proposals):
        product = proposal.get('selected_product') or {}
        match = proposal.get('pricebook_match') or {}
        verified = (product.get('sku') and match.get('status') in ('matched', 'needs_selection')
                    and canonical_brand(product.get('brand')) == canonical_brand(brand)
                    and not product.get('requires_confirmation')
                    and product.get('match_kind') != 'conditional_alternative')
        if not verified:
            product = next((candidate for candidates in (original.get('catalog_candidates') or {}).values()
                            for candidate in candidates if verified_web_product(candidate, brand, proposal)), None)
        if not product or (canonical_brand(original.get('brand')) == canonical_brand(brand)
                           and (original.get('part_number') or original.get('sku')) == product['sku']):
            result.append(deepcopy(original))
            continue
        updated = deepcopy(proposal if verified else original)
        observations = updated.setdefault('source_observations', {}) or {}
        updated['source_observations'] = observations
        observations.setdefault('quotation_source_identity', {key: original.get(key) for key in
                                ('brand', 'detected_brand', 'part_number', 'spec')})
        updated.update(brand=product['brand'], sku=product['sku'], part_number=product['sku'],
                       selected_product=deepcopy(product), selection_source='user_request',
                       unit_price=product.get('price'), price=product.get('price'), catalog_matches={})
        if not verified:
            updated['pricebook_match'] = None
        updated['catalog_candidates'] = {**deepcopy(original.get('catalog_candidates') or {}),
                                         **deepcopy(proposal.get('catalog_candidates') or {})}
        result.append(updated)
        changed += 1
    return result, changed


async def research_brand_replacements(devices, brand, db):
    """Try published data first, then research unresolved rows as one grounded batch."""
    items, _ = await asyncio.to_thread(compatible_brand_replacements, devices, brand)
    if not brand:
        return items, 0
    unresolved = [index for index, (source, item) in enumerate(zip(devices, items))
                  if item == source and canonical_brand(source.get('brand')) != canonical_brand(brand)
                  and source.get('selection_source') != 'approved_quotation']
    if unresolved:
        try:
            from app.schemas.ai import ExtractedDeviceSchema
            from app.services.ai.connection_pool import ConnectionPoolService
            from app.services.ai.web_device_recommendations import research_device_products
            research = [ExtractedDeviceSchema(category=str(devices[i].get('category') or ''),
                name=str(devices[i].get('name') or ''), spec=str(devices[i].get('spec') or ''),
                poles=devices[i].get('poles'), in_a=devices[i].get('in_a'), icu_ka=devices[i].get('icu_ka'),
                parent_compatibility=devices[i].get('parent_compatibility')) for i in unresolved]
            connections = await ConnectionPoolService.get_ordered_connections(db)
            await research_device_products(research, connections, db, preferred_brand=brand, requested_brand_only=True)
            for index, found in zip(unresolved, research):
                trial = deepcopy(devices[index])
                trial['catalog_candidates'] = found.catalog_candidates or {}
                replacement, count = compatible_brand_replacements([trial], brand, rows=[])
                if count:
                    items[index] = replacement[0]
                    items[index]['catalog_candidates'] = {**deepcopy(devices[index].get('catalog_candidates') or {}),
                                                          **(found.catalog_candidates or {})}
                    items[index]['web_research'] = found.web_research
        except Exception:
            logging.getLogger(__name__).exception('Brand research unavailable; keeping original devices')
    return items, sum(item != source for source, item in zip(devices, items))

"""Retain explicit device identity and installation review without guessing SKUs."""
from copy import deepcopy
from app.services.cad.device_installation import installation_review, category_code

EMPTY = {'', '-', '—', 'none', 'null', 'n/a', 'chưa chọn', 'theo thiết kế', 'thiết bị điện', 'unknown'}
NON_PRODUCT = {'LABOR','TEST','INSTALLATION','PACKAGE','SERVICE','DRAWING','SOURCE_REFERENCE','ASSEMBLY_REFERENCE'}


def text(value):
    value = str(value or '').strip()
    return '' if value.casefold() in EMPTY else value


def enrich_device_facts(source):
    row = deepcopy(source)
    kind = category_code(row.get('category'))
    required = kind not in NON_PRODUCT and not row.get('commercial_package')
    evidence = {}
    observations = row.get('source_observations') if isinstance(row.get('source_observations'),dict) else {}
    quote = observations.get('quotation') if isinstance(observations.get('quotation'),dict) else {}
    schematic = observations.get('schematic') if isinstance(observations.get('schematic'),dict) else {}
    match = row.get('pricebook_match') if isinstance(row.get('pricebook_match'),dict) else {}
    priced = match.get('row') if match.get('status')=='matched' and isinstance(match.get('row'),dict) else {}
    for field, candidates in (
        ('brand', [('brand',row.get('brand')), ('detected_brand',row.get('detected_brand')),
            ('manufacturer',row.get('manufacturer')), ('quotation.brand',quote.get('brand')),
            ('schematic.brand',schematic.get('brand')), ('matched_price_row.brand',priced.get('brand'))]),
        ('part_number', [('part_number',row.get('part_number')), ('model',row.get('model')),
            ('sku',row.get('sku')), ('quotation.model',quote.get('model')),
            ('schematic.model',schematic.get('model')), ('matched_price_row.sku',priced.get('sku'))]),
    ):
        available = [(key,text(value)) for key,value in candidates if text(value)]
        existing = text(row.get(field))
        if existing:
            evidence[field] = {'status':'retained','source_field':field}
        elif required and available:
            unique = {value.casefold() for _,value in available}
            if len(unique) == 1:
                row[field] = available[0][1]
                evidence[field] = {'status':'backfilled_explicit','source_field':available[0][0]}
            else:
                evidence[field] = {'status':'conflicting_source_fields','source_fields':[key for key,_ in available]}
        else:
            evidence[field] = {'status':'missing' if required else 'not_applicable'}
    # Already reviewed CAD policy remains attached. A kind-only review cannot
    # grant any actual mounting/cutout operation.
    row['installation_review'] = deepcopy(row.get('installation_review') or installation_review({},category=kind))
    row['identity_review'] = evidence
    row['identity_required'] = required
    return row


def enrich_quotation_facts(rows, devices=()):
    """Link only unique panel+tag evidence; never match a row by its position/name."""
    result=[]; panel=None
    for source in rows:
        row=deepcopy(source)
        if row.get('row_type')=='panel_header':
            panel=row.get('panel_code')
            if not panel and str(row.get('id','')).endswith('-header'):
                panel=row['id'][:-7]
        if row.get('row_type') not in {'item','accessory'}:
            result.append(row);continue
        tags=set(row.get('source_tags') or [])
        matches=[d for d in devices if d.get('tag') in tags and d.get('panel_code')==(row.get('panel_code') or panel)]
        facts = [enrich_device_facts(d) for d in matches]
        # A merged quotation row must have the same identity for every source tag.
        fact = facts[0] if facts and len(facts)==len(tags) and all(
            (d.get('brand'),d.get('part_number'),d.get('category')) ==
            (facts[0].get('brand'),facts[0].get('part_number'),facts[0].get('category')) for d in facts) else None
        if fact:
            if not text(row.get('origin')) and text(fact.get('brand')):row['origin']=fact['brand']
            if not text(row.get('sku')) and text(fact.get('part_number')):row['sku']=fact['part_number']
            row.setdefault('category',fact.get('category'))
            row['installation_review']=deepcopy(fact['installation_review'])
            if fact.get('installation_observation'):
                row['installation_observation']=deepcopy(fact['installation_observation'])
            row['installation_instances']=[dict(tag=d.get('tag'),panel_code=d.get('panel_code'),
                body_mount_face=d.get('mounting_face'),observation=deepcopy(d.get('installation_observation')))
                for d in facts]
        own = enrich_device_facts({**row,'brand':row.get('origin'),'part_number':row.get('sku')})
        if not text(row.get('origin')) and text(own.get('brand')):row['origin']=own['brand']
        if not text(row.get('sku')) and text(own.get('part_number')):row['sku']=own['part_number']
        row['identity_review']=own['identity_review']
        row['identity_required']=own['identity_required']
        row['installation_review']=own['installation_review']
        result.append(row)
    return result

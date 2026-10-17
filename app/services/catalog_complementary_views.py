"""Join complementary projections only when their product configuration agrees."""
import json
from collections import defaultdict
from .customer_equipment_information import product_specs
from .ai.manufacturer_registry import canonical_brand


def merge_complementary_views(profiles):
    groups=defaultdict(list)
    for profile in profiles:
        model=str(profile.get('product_code') or '').strip()
        specs=product_specs(profile.get('spec'))
        # An unresolved family label alone is insufficient to join drawings.
        if not model or model.startswith('*') or not profile.get('brand') or not specs.get('so_cuc'):continue
        if profile.get('type') in {'ASSEMBLY_REFERENCE','SOURCE_REFERENCE'}:continue
        key=(canonical_brand(profile['brand']),model.casefold(),profile.get('type'),
             json.dumps(specs,sort_keys=True,ensure_ascii=False))
        groups[key].append(profile)
    removed=set()
    for members in groups.values():
        if len(members)<2:continue
        faces=[v.get('face') for p in members for v in p['views']]
        # Repeated or unspecified faces may be different physical variants.
        if len(set(faces))!=len(faces) or not set(faces)<= {'Mặt trước','Mặt bên','Mặt trên','Mặt dưới','Mặt sau'}:continue
        target=next((p for p in members if any(v['face']=='Mặt trước' for v in p['views'])),members[0])
        target['views']=[v for p in members for v in p['views']]
        target['primary_view']=next((v['id'] for v in target['views'] if v['face']=='Mặt trước'),target['views'][0]['id'])
        target['member_profile_ids']=sorted({mid for p in members for mid in p.get('member_profile_ids',[p['id']])})
        options={}
        for p in members:
            for o in (p.get('catalog_references') or {}).get('options',[]):
                options.setdefault((o.get('brand'),o.get('model')),o)
        target['catalog_references']={**(target.get('catalog_references') or {}),'options':list(options.values())}
        removed.update(p['id'] for p in members if p is not target)
    result=[p for p in profiles if p['id'] not in removed]
    duplicates=defaultdict(list)
    for p in result:
        if p.get('product_code'):duplicates[(canonical_brand(p.get('brand')),p['product_code'])].append(p)
    for members in duplicates.values():
        if len(members)<2:continue
        for p in members:
            poles=(p.get('spec') or {}).get('so_cuc')
            if poles and str(poles) not in p['display']:
                p['display']+=' · '+str(poles)
            if poles:p['spec_hint']=str(poles)
    return result

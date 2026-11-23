"""Keep user choices separate from engineering proposals and materialize opt-ins."""
import math


def merge_proposal_choices(proposals, previous):
    by_key = {str(p.get('category')): p for p in previous or [] if isinstance(p, dict)}
    fields = ('use_in_quotation', 'quantity', 'brand', 'spec', 'part_number', 'sku',
              'selected_product', 'selection_source', 'pricebook_match', 'catalog_candidates')
    result = []
    for proposal in proposals:
        old = by_key.pop(str(proposal.get('category')), {})
        choice = {key: old[key] for key in fields if key in old}
        result.append({**proposal, **choice, 'included_in_total': old.get('use_in_quotation') is True})
    # A refresh must not silently discard an accessory the user chose to use.
    result.extend({**old, 'included_in_total': True} for old in by_key.values()
                  if old.get('use_in_quotation') is True)
    return result


def materialize_selected_accessories(devices):
    def positive(value):
        if isinstance(value, bool) or value in (None, ''):
            return None
        try:
            number = float(value)
            return number if math.isfinite(number) and number > 0 else None
        except (ValueError, TypeError):
            return None

    for device in devices:
        observations = device.get('source_observations') or {}
        assembly = observations.get('motor_starter') or observations.get('assembly') or {}
        accessories = [a for a in device.get('accompanying_accessories') or []
                       if not isinstance(a, dict) or not a.get('assembly_proposal_key')]
        proposed = [(p, None) for p in assembly.get('accessory_proposals') or []]
        for index, component in enumerate(assembly.get('components') or []):
            if isinstance(component, dict):
                key = str(component.get('component_key') or f'{component.get("category")}:{component.get("name")}:{index}')
                proposed.append((component, key))
        for proposal, component_key in proposed:
            if not isinstance(proposal, dict) or proposal.get('use_in_quotation') is not True:
                continue
            per_set = positive(proposal.get('quantity'))
            sets = positive(device.get('quantity', 1))
            quantity = per_set * sets if per_set is not None and sets is not None else None
            product = proposal.get('selected_product') or {}
            accessories.append({**proposal, 'assembly_proposal_key': f'component:{component_key}' if component_key else str(proposal.get('category')),
                'assembly_component_key': component_key,
                'basis': 'user_request', 'included_in_total': True, 'inclusion_status': 'user_selected',
                'category': product.get('category') or proposal.get('category'),
                'quantity_per_assembly': per_set, 'quantity': quantity,
                'brand': proposal.get('brand') or product.get('brand') or '',
                'sku': proposal.get('part_number') or proposal.get('sku') or product.get('sku') or '',
                'part_number': proposal.get('part_number') or proposal.get('sku') or product.get('sku') or '',
                'notes': 'Thiết bị thành phần đã được người dùng chọn sử dụng.' if component_key else
                         'Phụ kiện đề xuất đã được người dùng chọn sử dụng.'})
        device['accompanying_accessories'] = accessories
    return devices

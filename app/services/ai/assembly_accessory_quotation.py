"""Update chosen accessory rows while preserving edited quotation prices."""
from copy import deepcopy
from app.services.ai.procurement_review import build_quotation_rows


def sync_accessory_quotation(devices, existing_rows):
    fresh = build_quotation_rows(devices, {}, refresh_prices=True)
    if not existing_rows:
        return fresh
    selected = [r for r in fresh if r.get('assembly_proposal_key')]
    parents = {r.get('id'): r for r in fresh if r.get('row_type') == 'item'}
    rows = [deepcopy(r) for r in existing_rows if not r.get('assembly_proposal_key')]
    price_fields = ('unit_price', 'line_total', 'price_status', 'pricing_basis', 'notes')
    for row in rows:
        snapshot = row.pop('assembly_component_price_snapshot', None)
        if snapshot is not None:
            for field in price_fields:
                row.pop(field, None)
            row.update(snapshot)
    for accessory in selected:
        parent = parents.get(accessory.get('parent_id'), {})
        tags = set(parent.get('source_tags') or [])
        code = str(parent.get('panel_code') or '')
        # Fresh item IDs encode the panel code, even when older saved rows do
        # not carry a panel_code on every item.
        if not code:
            code = str(accessory.get('parent_id') or '').rsplit('-device-', 1)[0]
        panel = ''
        target = None
        panel_end = None
        found_panel = False
        for index, row in enumerate(rows):
            if row.get('row_type') == 'panel_header':
                if panel == code and panel_end is None:
                    panel_end = index
                panel = str(row.get('panel_code') or row.get('name') or '')
            if panel != code:
                continue
            found_panel = True
            if row.get('row_type') == 'item' and (bool(tags.intersection(row.get('source_tags') or []))
                    if tags else row.get('id') == accessory.get('parent_id')):
                target = index
                break
        if target is not None:
            original = rows[target]
            if accessory.get('assembly_component_key') and len(original.get('source_tags') or []) > 1:
                # A saved quotation may have merged identical whole sets. Split
                # those sets before removing the whole-set price for one circuit.
                old_tags = set(original['source_tags'])
                parts = []
                for candidate in parents.values():
                    candidate_code = str(candidate.get('id') or '').rsplit('-device-', 1)[0]
                    if candidate_code != code or not old_tags.intersection(candidate.get('source_tags') or []):
                        continue
                    part = {**deepcopy(original), 'id': candidate['id'],
                            'source_tags': candidate.get('source_tags') or [], 'quantity': candidate.get('quantity')}
                    quantity, price = part.get('quantity'), part.get('unit_price')
                    part['line_total'] = quantity * price if quantity is not None and price is not None else None
                    parts.append(part)
                if parts:
                    rows[target:target + 1] = parts
                    target += next((i for i, part in enumerate(parts) if tags.intersection(part['source_tags'])), 0)
            if accessory.get('assembly_component_key') and 'assembly_component_price_snapshot' not in rows[target]:
                rows[target]['assembly_component_price_snapshot'] = {
                    field: rows[target][field] for field in price_fields if field in rows[target]}
                rows[target].update(unit_price=0, line_total=0, price_status='components',
                    pricing_basis='selected_components', notes='Giá tính theo các thiết bị thành phần đã chọn bên dưới.')
            accessory['parent_id'] = rows[target].get('id')
            end = target + 1
            while end < len(rows) and rows[end].get('parent_id') == accessory['parent_id']:
                end += 1
            rows.insert(end, accessory)
        else:
            # A manually edited quotation may no longer have the source row.
            # Keep the accessory in its source panel with its circuit reference.
            position = panel_end if panel_end is not None else len(rows)
            prefix = [] if found_panel else [dict(id=f'panel-{code}', row_type='panel_header', name=code, panel_code=code, quantity=1)]
            rows[position:position] = [*prefix, dict(id=f'{accessory["id"]}-section', row_type='section_header',
                name=f'Thiết bị đã chọn · {code} · {", ".join(tags)}'), accessory]
    return rows

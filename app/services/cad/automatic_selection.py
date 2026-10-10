"""Select library geometry in the backend and retain reasons for rejected assets."""
import re
from .catalogtb_assets import candidates, resolve, instance_count
from .device_envelope import selected_envelope


def select_device_geometry(device, *, allow_preference_fallback=True):
    row = dict(device)
    cad = dict(row.get('cad') or {})
    # Typed fields may be omitted by extraction even when the source's literal
    # specification is retained. Never treat that omission as unrestricted poles.
    source_spec = str(row.get('spec') or '')
    for field, pattern in (
        ('poles', r'(?<!\w)([1-4])\s*P\b'),
        ('in_a', r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*A\b'),
        ('icu_ka', r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*k\s*A\b'),
    ):
        matches = re.findall(pattern, source_spec, re.I)
        values = {float(value.replace(',', '.')) for value in matches}
        if len(values) == 1 and row.get(field) is not None and float(row[field]) not in values:
            cad.pop('asset_id', None)
            cad['requires_selection'] = True
            cad['automatic_selection'] = {'status': 'unresolved', 'reason': 'source_spec_conflict',
                'field': field, 'typed_value': row[field], 'literal_value': next(iter(values))}
            row['cad'] = cad
            row.pop('dimensions', None)
            return row
    if row.get('poles') is None:
        match = re.search(r'(?<!\w)([1-4])\s*P\b', source_spec, re.I)
        if match:
            row['poles'] = int(match[1])
    if row.get('in_a') is None:
        match = re.search(r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*A\b', source_spec, re.I)
        if match:
            row['in_a'] = float(match[1].replace(',', '.'))
    if row.get('icu_ka') is None:
        match = re.search(r'(?<![\w.])(\d+(?:[.,]\d+)?)\s*k\s*A\b', source_spec, re.I)
        if match:
            row['icu_ka'] = float(match[1].replace(',', '.'))
    selected_asset = resolve(cad['asset_id']) if cad.get('asset_id') else None
    if cad.get('selection_source') == 'automatic_compatible_catalog_geometry':
        selected_asset = None
        row.pop('dimensions', None)
        cad.pop('geometry_dimensions_mm', None)
        cad.pop('electrical_selection_proposals', None)
    cad.pop('asset_id', None)
    category = str(row.get('category') or '').upper()
    brand = row.get('detected_brand') or row.get('brand')
    if str(brand or '').strip().casefold() == 'asian':
        brand = None  # User's unspecified-brand label, not a verified manufacturer.
    poles = row.get('poles')
    pool = candidates(category, brand, poles)
    library_candidate_count = len(pool)
    if selected_asset:
        pool = [asset for asset in pool if asset['id'] == selected_asset['id']]
    model = str(row.get('part_number') or '').strip().upper()
    if model:
        pool = [a for a in pool if re.search(r'(?<![A-Z0-9])' + re.escape(model) + r'(?![A-Z0-9])',
                                          ' '.join([a['name'], *a['search_aliases']]).upper())]
    eligible, rejected = [], []
    for asset in pool:
        try:
            specs = asset.get('specifications') or {}
            current = row.get('in_a')
            proposals = [v for v in asset.get('electrical_variants', [])
                         if v['current_a'] == current and v['poles'] == row.get('poles')
                         and v['icn_ka'] >= float(row.get('icu_ka') or 0)]
            if proposals:
                # Preserve the manufacturer's Icn designation; this does not
                # certify Icu at the project's voltage or exact CAD/SKU identity.
                specs = {**specs, 'dong_dinh_muc': str(current),
                         'kha_nang_cat': str(proposals[0]['icn_ka']) + ' kA'}
            current_text = str(specs.get('dong_dinh_muc') or '')
            numbers = [float(n.replace(',', '.')) for n in re.findall(r'\d+(?:\.\d+)?', current_text)]
            if category in ('MCB', 'MCCB', 'RCBO', 'RCCB') and current and not numbers:
                raise ValueError('Hồ sơ chưa có dải dòng điện để đối chiếu')
            if current and numbers:
                interval = re.search(r'(\d+(?:\.\d+)?)\s*[–—-]\s*(\d+(?:\.\d+)?)', current_text)
                if interval:
                    compatible = float(interval[1]) <= float(current) <= float(interval[2])
                else:
                    compatible = float(current) in numbers
                if not compatible:
                    raise ValueError('Dòng yêu cầu nằm ngoài biến thể trong hồ sơ')
            requested_icu = row.get('icu_ka')
            capacities = [float(n.replace(',', '.')) for n in re.findall(
                r'(\d+(?:[.,]\d+)?)\s*k\s*A', str(specs.get('kha_nang_cat') or ''), re.I)]
            if requested_icu and not capacities:
                raise ValueError('Hồ sơ chưa có khả năng cắt để đối chiếu')
            if requested_icu and capacities and max(capacities) < float(requested_icu):
                raise ValueError('Khả năng cắt trong hồ sơ thấp hơn yêu cầu')
            instance_count(row.get('quantity') or 1, asset)
            probe = {**row, 'cad': {**cad, 'asset_id': asset['id']}}
            dimensions = selected_envelope(probe)
            eligible.append(({**asset, 'selection_proposals': proposals}, dimensions))
        except (ValueError, KeyError, FileNotFoundError) as exc:
            rejected.append({'asset_id': asset['id'], 'reason': str(exc)})
    if not eligible and not selected_asset and brand and not model and allow_preference_fallback and row.get('selection_source') == 'default_brand':
        fallback = select_device_geometry({**row, 'brand': None, 'cad': cad}, allow_preference_fallback=False)
        if (fallback.get('cad') or {}).get('asset_id'):
            fallback['cad']['preferred_brand'] = brand
            return fallback
    # A geometry proposal is distinct from an exact priced or fabrication SKU.
    # Prefer the smallest complete mounting envelope among compatible families.
    if eligible and (len(eligible) == 1 or not model and row.get('selection_source') == 'default_brand'):
        asset, dimensions = min(eligible, key=lambda item: (
            item[1][0] * item[1][1] * item[1][2], item[0]['id']))
        cad.update(asset_id=asset['id'], requires_selection=False,
                   selection_source='automatic_compatible_catalog_geometry',
                   exact_model=False, geometry_dimensions_mm=list(dimensions))
        cad['electrical_selection_proposals'] = asset.get('selection_proposals', [])
        row['brand'] = asset['brand']
        row['dimensions'] = dict(zip(('w', 'h', 'd'), dimensions))
    cad['automatic_selection'] = {
        'requested_model': model or None,
        'library_candidate_count': library_candidate_count,
        'status': 'selected' if cad.get('asset_id') else 'unresolved',
        'eligible_asset_ids': [a['id'] for a, _ in eligible],
        'rejected': rejected,
        'reason': None if cad.get('asset_id') else
                  'ambiguous_family' if len(eligible) > 1 else
                  'model_not_bound_to_source_geometry' if model and not pool else 'no_verified_geometry_match',
    }
    cad['requires_selection'] = not bool(cad.get('asset_id'))
    row['cad'] = cad
    return row

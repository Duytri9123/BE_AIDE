"""Select library geometry in the backend and retain reasons for rejected assets."""
import re
import unicodedata
from .catalogtb_assets import candidates, resolve, instance_count
from .device_envelope import selected_envelope


def select_device_geometry(device, *, allow_preference_fallback=True, allow_unverified_electrical=False):
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
    try:
        selected_asset = resolve(cad['asset_id']) if cad.get('asset_id') else None
    except ValueError:
        # A saved project can outlive a reviewed library asset. Retain the
        # user's electrical choice, but never silently replace its geometry.
        unavailable = cad.pop('asset_id')
        cad.pop('geometry_dimensions_mm', None)
        cad.pop('geometry_dimensions_status', None)
        cad['unavailable_asset_id'] = unavailable
        cad['requires_selection'] = True
        cad['automatic_selection'] = {'status':'unresolved', 'reason':'selected_asset_unavailable'}
        row['cad'] = cad
        row.pop('dimensions', None)
        return row
    if cad.get('selection_source') == 'automatic_compatible_catalog_geometry':
        selected_asset = None
        row.pop('dimensions', None)
        cad.pop('geometry_dimensions_mm', None)
        cad.pop('electrical_selection_proposals', None)
    cad.pop('asset_id', None)
    cad.pop('geometry_dimensions_status', None)
    category = str(row.get('category') or '').upper()
    source_category = category
    category = {'SELECTOR SWITCH': 'SELECTOR', 'SELECTOR_SWITCH': 'SELECTOR',
                'VOLTMETER': 'METER', 'AMMETER': 'METER'}.get(category, category)
    description = ' '.join(str(row.get(key) or '') for key in ('name', 'spec', 'electrical_function'))
    normalized = ''.join(c for c in unicodedata.normalize('NFD', description.casefold())
                         if not unicodedata.combining(c)).replace('đ', 'd')
    measurement = ('voltage' if re.search(r'von ke|volt(?:meter)?|chon dien ap', normalized)
                   else 'current' if re.search(r'ampe ke|ammeter|chon dong dien', normalized) else None)
    if source_category in ('VOLTMETER', 'AMMETER'):
        measurement = 'voltage' if source_category == 'VOLTMETER' else 'current'
    if category not in ('METER', 'SELECTOR', 'SWITCH'):
        measurement = None
    if category == 'SWITCH' and measurement:
        category = 'SELECTOR'
    # Historical extraction used Asia for the user's unspecified-brand label.
    # Keep the source value for traceability; never filter the catalog by it.
    for field in ('brand', 'detected_brand'):
        if str(row.get(field) or '').strip().casefold() == 'asia':
            row.setdefault('source_brand_label', row[field])
            row[field] = 'Asian'
    brand = row.get('detected_brand') or row.get('brand')
    if str(brand or '').strip().casefold() == 'asian':
        brand = None  # User's unspecified-brand label, not a verified manufacturer.
    poles = row.get('poles')
    kinds = ('MCB', 'MCCB') if category == 'CB' and poles else (category,)
    pool = [a for kind in kinds for a in candidates(kind, brand, poles, measurement_function=measurement)]
    library_candidate_count = len(pool)
    if selected_asset:
        pool = [asset for asset in pool if asset['id'] == selected_asset['id']]
    model = str(row.get('part_number') or '').strip().upper()
    if model:
        pool = [a for a in pool if (
            any(re.match(re.escape(str(code).upper())+r'(?=$|[\s/_.-])',model) for code in a['model_codes'])
            if a.get('model_codes') else
            re.search(r'(?<![A-Z0-9])' + re.escape(model) + r'(?![A-Z0-9])',
                      ' '.join([a['name'], *a['search_aliases']]).upper()))]
    eligible, rejected, matched_geometry = [], [], []
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
            # A verified family envelope is useful in a reference layout even
            # when its exact electrical variant is not identified. It never
            # establishes a procurement SKU or electrical approval.
            electrical_review = bool(current and not numbers)
            from .ls_view_coverage import is_ls
            if is_ls(asset.get('brand')) and category == 'CONTACTOR':
                from app.services.catalog_product_sections import current_kinds
                wanted=current_kinds(source_spec+' '+str(row.get('coil_voltage') or ''))
                actual=current_kinds(specs.get('Loại cuộn hút') or specs.get('dien_ap_cuon_hut'))
                if wanted and actual and not wanted.issubset(actual):
                    raise ValueError('Loại cuộn hút AC/DC của CAD LS không đúng yêu cầu')
                if wanted and not actual:
                    if not allow_unverified_electrical:raise ValueError('CAD LS chưa xác nhận loại cuộn hút AC/DC')
                    electrical_review=True
                from app.services.catalog_product_sections import auxiliary_contacts
                wanted_aux=auxiliary_contacts(source_spec)
                actual_aux=auxiliary_contacts(specs.get('Tiếp điểm phụ'))
                if wanted_aux is not None and actual_aux is not None and wanted_aux!=actual_aux:
                    raise ValueError('Tiếp điểm phụ của CAD LS không đúng cấu hình 1a1b/2a2b yêu cầu')
                if wanted_aux is not None and actual_aux is None:electrical_review=True
            if electrical_review and not allow_unverified_electrical:
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
            if (category in {'CB', 'MCB', 'MCCB', 'ACB', 'RCBO', 'RCCB'} or is_ls(asset.get('brand')) and category in {'ELCB','MOTOR_PROTECTION'}) and not requested_icu:
                electrical_review = True
            capacities = [float(n.replace(',', '.')) for n in re.findall(
                r'(\d+(?:[.,]\d+)?)\s*k\s*A', str(specs.get('kha_nang_cat') or ''), re.I)]
            electrical_review = electrical_review or bool(requested_icu and not capacities)
            if requested_icu and not capacities and not allow_unverified_electrical:
                raise ValueError('Hồ sơ chưa có khả năng cắt để đối chiếu')
            if requested_icu and capacities and min(capacities) < float(requested_icu):
                raise ValueError('Khả năng cắt trong hồ sơ thấp hơn yêu cầu')
            instance_count(row.get('quantity') or 1, asset)
            from .ls_view_coverage import require_complete_ls_views
            require_complete_ls_views(asset)
            matched_geometry.append(asset)
            probe = {**row, 'cad': {**cad, 'asset_id': asset['id']}}
            dimensions = selected_envelope(probe)
            eligible.append(({**asset, 'selection_proposals': proposals,
                              'electrical_review': electrical_review}, dimensions))
        except (ValueError, KeyError, FileNotFoundError) as exc:
            rejected.append({'asset_id': asset['id'], 'reason': str(exc)})
    from app.services.library_review_scope import MAIN_DEVICE_TYPES, DEPENDENT_ACCESSORY_TYPES
    if (not eligible and not selected_asset and brand and not model and allow_preference_fallback
            and category not in MAIN_DEVICE_TYPES | DEPENDENT_ACCESSORY_TYPES
            and row.get('selection_source') == 'default_brand'):
        fallback = select_device_geometry({**row, 'brand': None, 'cad': cad}, allow_preference_fallback=False,
                                          allow_unverified_electrical=allow_unverified_electrical)
        if (fallback.get('cad') or {}).get('asset_id'):
            fallback['cad']['preferred_brand'] = brand
            return fallback
    # A geometry proposal is distinct from an exact priced or fabrication SKU.
    # Prefer the smallest complete mounting envelope among compatible families.
    if eligible and (len(eligible) == 1 or not model and row.get('selection_source') in ('default_brand', 'unspecified_brand')):
        asset, dimensions = min(eligible, key=lambda item: (
            bool(item[0].get('electrical_review')),
            (-1 if category == 'MCCB' and item[0].get('electrical_review') else 1)
            * item[1][0] * item[1][1] * item[1][2], item[0]['id']))
        cad.update(asset_id=asset['id'], requires_selection=False,
                   selection_source='automatic_compatible_catalog_geometry',
                   exact_model=False, geometry_dimensions_mm=list(dimensions))
        cad['electrical_selection_proposals'] = asset.get('selection_proposals', [])
        cad['geometry_brand'] = asset['brand']
        cad['geometry_category'] = asset['category']
        cad['electrical_verification_required'] = asset.get('electrical_review', False)
        if str(row.get('brand') or '').casefold() != 'asian':
            row['brand'] = asset['brand']
        if category != source_category:
            row['source_category'] = source_category
            row['category'] = category
            cad['role_normalization'] = 'explicit_measurement_selector_function'
        row['dimensions'] = dict(zip(('w', 'h', 'd'), dimensions))
    elif len(matched_geometry) == 1 and not eligible:
        # A missing side view is missing engineering data, not absent CAD.
        # Keep the real matched view available for review, without sizing it.
        asset = matched_geometry[0]
        cad.update(asset_id=asset['id'], requires_selection=False,
                   selection_source='automatic_compatible_catalog_geometry',
                   exact_model=False, geometry_dimensions_status='requires_depth_or_mounting_review')
        cad.pop('geometry_dimensions_mm', None)
        row.pop('dimensions', None)
    cad['automatic_selection'] = {
        'requested_model': model or None,
        'library_candidate_count': library_candidate_count,
        'status': 'selected' if cad.get('asset_id') else 'unresolved',
        'eligible_asset_ids': [a['id'] for a, _ in eligible],
        'matched_asset_ids': [a['id'] for a in matched_geometry],
        'rejected': rejected,
        'reason': 'matched_cad_missing_envelope' if matched_geometry and not eligible else None if cad.get('asset_id') else
                  'ambiguous_family' if len(eligible) > 1 else
                  'model_not_bound_to_source_geometry' if model and not pool else 'no_verified_geometry_match',
    }
    cad['requires_selection'] = not bool(cad.get('asset_id'))
    from .ls_view_coverage import is_ls
    if is_ls(brand) and not cad.get('asset_id'):
        cad['supplement_required'] = True
        cad['supplement_reason'] = 'LS cần CAD đúng mã/họ và đủ mặt trước, sau, trái, phải, trên, dưới cùng biến thể trước khi bố trí.'
    row['cad'] = cad
    return row

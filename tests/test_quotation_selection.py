from copy import deepcopy
from unittest.mock import patch

from app.services.ai.quotation_selection import select_quotation_devices
from app.services.export.quotation_exporter import QuotationExporterService


def price_row(maker='LS Electric', sku='LS16', current=16, icu=10):
    return dict(id=maker+sku, brand=maker, sku=sku, item_name=f'MCB {sku}',
                category='MCB', price=120000, specifications={
                    'Số cực': '1P', 'In (A)': str(current), 'Icu (kA)': str(icu)})


def device(**changes):
    return dict(category='MCB', name='Bảo vệ nhánh chiếu sáng L1 dài từ bản vẽ',
                spec='1P-16A-6kA', poles=1, in_a=16, icu_ka=6, quantity=2, **changes)


def test_common_brand_selects_same_maker_replacement_and_preserves_source():
    source = device(brand='ABB', part_number='OLD')
    original = deepcopy(source)
    selected = select_quotation_devices([source], 'LS', [price_row(), price_row('ABB', 'ABB16')])[0]
    assert source == original
    assert selected['brand'] == 'LS Electric'
    assert selected['part_number'] == 'LS16'
    assert selected['source_observations']['quotation_source_identity']['part_number'] == 'OLD'


def test_missing_same_brand_product_does_not_choose_other_brand_or_stale_price():
    selected = select_quotation_devices([device(brand='ABB', part_number='OLD', unit_price=999)],
                                       'LS', [price_row('ABB', 'ABB16')])[0]
    assert selected['brand'] == 'LS Electric'
    assert not selected['part_number']
    assert selected['unit_price'] is None


def test_explicit_row_choice_survives_common_default():
    source = device(brand='ABB', part_number='ABB16', selection_source='user_selected')
    assert select_quotation_devices([source], 'Theo thiết kế', [price_row()])[0] == source


def test_explicit_brand_changes_main_devices_only_and_keeps_proposal_unpriced():
    from app.services.ai.procurement_review import build_quotation_rows

    breaker = {**device(brand='ABB', part_number='OLD', selection_source='user_selected'),
               'in_a': 30, 'spec': '30A 1P 6kA', 'section': 'Đầu ra'}
    accessory = dict(category='LIGHT', brand='Mikro', name='Đèn báo', quantity=1, section='Đầu vào')
    selected = select_quotation_devices([breaker, accessory], 'LS', [price_row(current=32, icu=6)])
    assert selected[0]['brand'] == 'LS Electric'
    assert selected[0]['in_a'] == 30
    assert selected[0]['part_number'] == ''
    assert selected[1] == accessory
    rows = build_quotation_rows(selected, {}, refresh_prices=False)
    assert [row['name'] for row in rows if row['row_type'] == 'section_header'] == [
        'Vỏ tủ + phụ kiện', 'Đo lường & Giám sát', 'Đầu ra']
    proposed = next(row for row in rows if row.get('category') == 'MCB')
    assert proposed['spec'] == '30A 1P 6kA => 32A 1P 6kA'
    assert proposed['unit_price'] is None
    assert 'LS16' in proposed['notes']


def test_exact_current_wins_and_lower_breaking_capacity_cannot_be_proposed():
    source = {**device(brand='ABB'), 'in_a': 30, 'spec': '30A 1P 6kA'}
    rows = [price_row(sku='LS30', current=30, icu=6), price_row(sku='LS32', current=32, icu=6)]
    assert select_quotation_devices([source], 'LS', rows)[0]['part_number'] == 'LS30'
    selected = select_quotation_devices([source], 'LS', [price_row(current=32, icu=4)])[0]
    assert not selected['catalog_candidates']


def test_wrong_rating_is_never_automatically_substituted():
    for row in [price_row(current=20), price_row(icu=4)]:
        assert not select_quotation_devices([device()], 'LS', [row])[0].get('part_number')


def test_quote_is_commercial_row_with_selected_sku_and_price():
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[price_row()]):
        result = QuotationExporterService.match_devices_multi_brand([device()], 'LS')[0]
    assert result['name'] == 'MCB · 1P-16A-6kA'
    assert result['sku'] == 'LS16'
    assert result['unit_price'] == 120000
    assert result['line_total'] == 240000


def test_unpriced_quote_keeps_price_pending():
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[]):
        result = QuotationExporterService.match_devices_multi_brand([device()], 'LS')[0]
    assert result['unit_price'] is None
    assert result['line_total'] is None


def test_change_common_brand_replaces_sku_and_retains_original_evidence():
    rows = [price_row(), price_row('ABB', 'ABB16')]
    first = select_quotation_devices([device(brand='Old', part_number='ORIGINAL')], 'LS', rows)
    second = select_quotation_devices(first, 'ABB', rows)[0]
    assert second['brand'] == 'ABB'
    assert second['part_number'] == 'ABB16'
    assert second['source_observations']['quotation_source_identity']['part_number'] == 'ORIGINAL'


def test_specs_can_supply_missing_numeric_fields():
    source = device()
    for key in ('poles', 'in_a', 'icu_ka'):
        source.pop(key)
    assert select_quotation_devices([source], 'LS', [price_row()])[0]['part_number'] == 'LS16'


def test_explicit_row_selection_uses_selected_maker_instead_of_drawing_maker():
    from app.services.library_review_scope import preferred_brand_for_device
    source = device(brand='ABB', detected_brand='LS', part_number='ABB16', selection_source='user_selected')
    assert preferred_brand_for_device(source, 'LS') == 'ABB'

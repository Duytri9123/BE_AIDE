from copy import deepcopy
from unittest.mock import patch

from app.services.ai.assembly_accessory_catalog import accessory_catalog_options
from app.services.ai.assembly_accessory_selection import materialize_selected_accessories
from app.services.ai.motor_starter_context import enrich_motor_starters
from app.services.ai.procurement_review import build_quotation_rows
from app.services.ai.cluster_equipment_service import AccompanyingEquipmentService


def price_rows():
    return [dict(id='light-ls', category='LIGHT', item_name='Đèn báo 24V', sku='L24',
                 brand='LS Electric', price=100, specifications={}),
            dict(id='light-abb', category='LIGHT', item_name='Đèn báo 24V', sku='A24',
                 brand='ABB', price=200, specifications={})]


def starter(selected=True, quantity=2, accessory_quantity=3):
    return dict(name='DOL', category='DOL', tag='L1', panel_code='P1', quantity=quantity,
        source_observations={'motor_starter': {'type': 'DOL', 'accessory_proposals': [dict(
            category='RUN_INDICATOR', name='Đèn báo chạy', quantity=accessory_quantity,
            use_in_quotation=selected, brand='LS Electric', part_number='L24', selection_source='user_selected',
            selected_product={'category': 'LIGHT', 'brand': 'LS Electric', 'sku': 'L24'})]}})


def accessory_rows(device):
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=price_rows()):
        return [r for r in build_quotation_rows([device], {}, refresh_prices=True)
                if r.get('assembly_proposal_key')]


def test_only_opted_in_parts_are_quoted_with_selected_brand_sku_and_real_price():
    assert accessory_rows(starter(False)) == []
    row, = accessory_rows(starter())
    assert row['origin'] == 'LS Electric' and row['sku'] == 'L24'
    assert row['quantity'] == 6 and row['unit_price'] == 100 and row['line_total'] == 600
    assert row['inclusion_status'] == 'user_selected' and row['parent_id'] == 'P1-device-0'


def test_unknown_quantity_or_code_is_pending_without_invented_values():
    row, = accessory_rows(starter(accessory_quantity=None))
    assert row['quantity'] is None and row['line_total'] is None and row['price_status'] == 'pending'
    device = starter()
    proposal = device['source_observations']['motor_starter']['accessory_proposals'][0]
    proposal.update(part_number='UNKNOWN', selected_product=None)
    row, = accessory_rows(device)
    assert row['sku'] == 'UNKNOWN' and row['unit_price'] is None


def test_refresh_and_repeated_build_preserve_choices_and_do_not_duplicate():
    device = starter()
    enrich_motor_starters([device])
    enrich_motor_starters([device])
    chosen = next(p for p in device['source_observations']['motor_starter']['accessory_proposals']
                  if p['category'] == 'RUN_INDICATOR')
    assert chosen['use_in_quotation'] is True and chosen['part_number'] == 'L24'
    materialize_selected_accessories([device])
    materialize_selected_accessories([device])
    assert len(device['accompanying_accessories']) == 1
    formatted = AccompanyingEquipmentService.format_accessories(device['accompanying_accessories'])
    assert len(formatted) == 1 and formatted[0]['quantity'] == 6 and formatted[0]['evidence'] == ''
    assert len(accessory_rows(device)) == 1
    chosen['use_in_quotation'] = False
    assert accessory_rows(device) == []


def test_catalog_filters_requested_role_and_brand_without_selecting_automatically():
    choices = accessory_catalog_options({'category': 'RUN_INDICATOR'}, 'LS', price_rows())
    assert [c['sku'] for c in choices] == ['L24']
    assert choices[0]['category'] == 'LIGHT' and choices[0]['auto_selectable'] is False


def test_decisions_do_not_leak_between_starters_or_modify_source_accessories():
    first, second = starter(), starter(False)
    first['accompanying_accessories'] = [{'name': 'Existing', 'quantity': 1, 'evidence': 'CAD'}]
    original = deepcopy(first['accompanying_accessories'])
    materialize_selected_accessories([first, second])
    assert first['accompanying_accessories'][0] == original[0]
    assert len(first['accompanying_accessories']) == 2 and second['accompanying_accessories'] == []


def test_live_quote_updates_preserve_existing_prices_and_remove_unchecked_parts():
    from app.services.ai.assembly_accessory_quotation import sync_accessory_quotation
    device = starter()
    old = [dict(id='panel-P1', row_type='panel_header', name='P1', panel_code='P1'),
           dict(id='P1-assembly-ENCLOSURE', row_type='item', commercial_package=True,
                unit_price=12345, line_total=12345, quantity=1),
           dict(id='custom-parent', row_type='item', name='DOL', source_tags=['L1', 'L2'],
                unit_price=999, line_total=999, quantity=1)]
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=price_rows()):
        rows = sync_accessory_quotation([device], old)
        assert rows[:3] == old
        assert rows[3]['parent_id'] == 'custom-parent' and rows[3]['line_total'] == 600
        rows = sync_accessory_quotation([device], rows)
        assert len([r for r in rows if r.get('assembly_proposal_key')]) == 1
        device['source_observations']['motor_starter']['accessory_proposals'][0]['use_in_quotation'] = False
        assert sync_accessory_quotation([device], rows) == old


def test_live_quote_keeps_repeated_circuit_tags_in_the_correct_panel():
    from app.services.ai.assembly_accessory_quotation import sync_accessory_quotation
    device = starter()
    device['panel_code'] = 'P2'
    old = [dict(id='h1', row_type='panel_header', name='P1'),
           dict(id='p1', row_type='item', name='DOL', source_tags=['L1']),
           dict(id='h2', row_type='panel_header', name='P2'),
           dict(id='p2', row_type='item', name='DOL', source_tags=['L1'])]
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=price_rows()):
        rows = sync_accessory_quotation([device], old)
    assert rows[4]['parent_id'] == 'p2'
    assert rows[:4] == old

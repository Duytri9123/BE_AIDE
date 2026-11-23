from copy import deepcopy
from unittest.mock import patch

from app.services.ai.assembly_accessory_catalog import accessory_catalog_options
from app.services.ai.assembly_accessory_quotation import sync_accessory_quotation
from app.services.ai.motor_starter_context import enrich_motor_starters
from app.services.ai.procurement_review import build_quotation_rows


def prices():
    return [dict(id=sku, sku=sku, brand='LS Electric', category=category, item_name=sku,
                 price=price, specifications={}) for sku, category, price in [
        ('KM1', 'CONTACTOR', 100), ('KM2', 'CONTACTOR', 200), ('KM3', 'CONTACTOR', 300),
        ('TOR', 'THERMAL_RELAY', 50), ('ON', 'PUSHBUTTON', 10), ('OFF', 'PUSHBUTTON', 20),
        ('SEL', 'SELECTOR_SWITCH', 30), ('FULL', 'DOL', 1000)]]


def picked(category, name, sku, actual=None, quantity=1):
    return dict(category=category, name=name, quantity=quantity, use_in_quotation=True,
        brand='LS Electric', part_number=sku, selection_source='user_selected',
        selected_product={'brand': 'LS Electric', 'sku': sku, 'category': actual or category})


def device(components, tag='L1', count=2, category='DOL'):
    return dict(name=category, category=category, tag=tag, quantity=count, panel_code='P1',
        brand='LS Electric', part_number='FULL',
        source_observations={'motor_starter': {'type': category, 'components': components}})


def build(devices):
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=prices()):
        return build_quotation_rows(devices, {}, refresh_prices=True)


def test_component_choices_survive_refresh_and_have_correct_prices_and_counts():
    components = [picked('CONTACTOR', 'Contactor', 'KM1'),
        picked('OVERLOAD_PROTECTION', 'Rơ le nhiệt', 'TOR', 'THERMAL_RELAY'),
        picked('PUSH_BUTTON_ON', 'Nút ON', 'ON', 'PUSHBUTTON'),
        picked('PUSH_BUTTON_OFF', 'Nút OFF', 'OFF', 'PUSHBUTTON'),
        picked('SELECTOR_SWITCH_3_POSITION', 'Công tắc 3 vị trí', 'SEL', 'SELECTOR_SWITCH')]
    source = device(components)
    enrich_motor_starters([source]); enrich_motor_starters([source])
    assert [c['part_number'] for c in source['source_observations']['motor_starter']['components']] == ['KM1', 'TOR', 'ON', 'OFF', 'SEL']
    rows = build([source])
    chosen = [r for r in rows if r.get('assembly_component_key')]
    assert [(r['sku'], r['quantity'], r['line_total']) for r in chosen] == [
        ('KM1', 2, 200), ('TOR', 2, 100), ('ON', 2, 20), ('OFF', 2, 40), ('SEL', 2, 60)]
    parent = next(r for r in rows if r.get('id') == 'P1-device-0')
    assert parent['unit_price'] == 0 and parent['line_total'] == 0
    assert parent['assembly_component_price_snapshot']['unit_price'] == 1000


def test_three_contactors_remain_independent_and_unchecking_removes_only_one():
    source = device([picked('CONTACTOR', 'KM-Main', 'KM1'), picked('CONTACTOR', 'KM-Delta', 'KM2'),
                     picked('CONTACTOR', 'KM-Star', 'KM3')], category='STAR_DELTA')
    rows = build([source])
    chosen = [r for r in rows if r.get('assembly_component_key')]
    assert len({r['assembly_component_key'] for r in chosen}) == 3
    assert [r['line_total'] for r in chosen] == [200, 400, 600]
    source['source_observations']['motor_starter']['components'][1]['use_in_quotation'] = False
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=prices()):
        updated = sync_accessory_quotation([source], rows)
    assert [r['sku'] for r in updated if r.get('assembly_component_key')] == ['KM1', 'KM3']


def test_live_quote_splits_merged_sets_and_restores_whole_set_price_when_unchecked():
    first = device([picked('CONTACTOR', 'Contactor', 'KM1')], count=1)
    second = device([], tag='L2', count=1)
    old = [dict(row_type='panel_header', id='panel-P1', name='P1'),
           dict(row_type='item', id='old', name='DOL', category='DOL', quantity=2,
                unit_price=1000, line_total=2000, source_tags=['L1', 'L2'])]
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=prices()):
        rows = sync_accessory_quotation([first, second], old)
        parents = [r for r in rows if r.get('row_type') == 'item']
        assert [(r['source_tags'], r['unit_price']) for r in parents] == [(['L1'], 0), (['L2'], 1000)]
        first['source_observations']['motor_starter']['components'][0]['use_in_quotation'] = False
        restored = sync_accessory_quotation([first, second], rows)
    assert not any(r.get('assembly_component_key') for r in restored)
    assert sum(r.get('line_total') or 0 for r in restored) == 2000
    assert old[1]['line_total'] == 2000


def test_unknown_component_quantity_stays_pending_and_catalog_roles_are_supported():
    source = device([picked('CONTACTOR', 'Contactor', 'KM1', quantity=None)])
    row, = [r for r in build([source]) if r.get('assembly_component_key')]
    assert row['quantity'] is None and row['unit_price'] is None and row['line_total'] is None
    for role, expected in [('CONTACTOR', ['KM1', 'KM2', 'KM3']),
                           ('OVERLOAD_PROTECTION', ['TOR']), ('PUSH_BUTTON_ON', ['ON', 'OFF']),
                           ('SELECTOR_SWITCH_3_POSITION', ['SEL'])]:
        choices = accessory_catalog_options({'category': role}, 'LS', prices())
        assert sorted(c['sku'] for c in choices) == sorted(expected)

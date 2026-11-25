from app.api.v1.endpoints.el_agent import standardize_quotation_table_and_rows
from app.services.ai.analysis_result import _build_analysis_result_schema
from app.services.ai.takeoff_catalog import suggest_takeoff_products


def test_ammeter_uses_only_the_linked_ct_and_prioritizes_verified_scale():
    meters = [
        dict(category='AMMETER', name='Đồng hồ ampe', panel_code='TĐ-HL.T30',
             upstream_device='TI1', tag='A1', quantity=3),
        dict(category='CT', name='Biến dòng', panel_code='TĐ-HL.T30', tag='TI1', spec='40A/5A'),
        dict(category='CT', name='Biến dòng', panel_code='TĐ-HL.T30', tag='TI2', spec='100/1A'),
        dict(category='AMMETER', name='Đồng hồ ampe', panel_code='TĐ-HL.T30', tag='A2'),
    ]
    pricebook = [
        dict(category='AMMETER', brand='LS', sku=sku, item_name=f'Ampe kế {description}', source_url='catalog.pdf')
        for sku, description in [('A40', '40/5 A'), ('A50', '50/5 A'), ('FAMILY', 'mặt 96 mm')]
    ]
    linked, _, _, ambiguous = suggest_takeoff_products(meters, catalog_rows=pricebook)
    assert linked['selection_analysis']['input_current_a'] == 5
    assert linked['selection_analysis']['display_range_a'] == [0, 40]
    assert not linked.get('spec') and linked['quantity'] == 3
    options = linked['catalog_candidates']['LS Electric']
    assert [(item['sku'], item['match_kind']) for item in options] == [('A40', 'meter_spec_match')]
    assert ambiguous['selection_analysis']['status'] == 'needs_context'
    assert all(item['match_kind'] == 'meter_reference' for item in ambiguous['catalog_candidates']['LS Electric'])


def test_quote_merges_repeated_branches_and_groups_metering_separately():
    markdown = (
        '| TT | MÔ TẢ CHI TIẾT | MÃ HÀNG | XUẤT XỨ | ĐƠN VỊ | SỐ LƯỢNG | ĐƠN GIÁ | THÀNH TIỀN | GHI CHÚ |\n'
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n'
        '| + | MCB 1P 10A 6kA | LS10 | LS | Cái | 1 | 100 | 100 | Lộ L1: Chiếu sáng |\n'
        '| + | MCB 1P 10A 6kA | LS10 | LS | Cái | 2 | 100 | 200 | Lộ L2: Chiếu sáng |\n'
        '| + | MCB 1P 16A 6kA | LS16 | LS | Cái | 1 | 100 | 100 | Lộ L3: Chiếu sáng |\n'
        '| + | MCB 3P 40A 10kA | MAIN40 | LS | Cái | 1 | 200 | 200 | Lộ tổng |\n'
        '| + | Đồng hồ ampe | | | Cái | 3 | 0 | 0 | Mạch đo |'
    )
    rendered, rows = standardize_quotation_table_and_rows(markdown)
    assert 'Lộ L' not in rendered and '400/5A' not in rendered
    assert set(r['name'] for r in rows if r['row_type'] == 'section_header') == {
        'Đầu vào', 'Đo lường & Giám sát', 'Đầu ra'}
    assert [r['quantity'] for r in rows if r.get('sku') == 'LS10'] == [3]
    assert [r['line_total'] for r in rows if r.get('sku') == 'LS10'] == [300]


def test_quote_does_not_merge_identical_items_across_cabinets():
    _, rows = standardize_quotation_table_and_rows(
        '| TT | MÔ TẢ CHI TIẾT | MÃ HÀNG | XUẤT XỨ | ĐƠN VỊ | SỐ LƯỢNG | ĐƠN GIÁ | THÀNH TIỀN | GHI CHÚ |\n'
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n'
        '| 1 | **TỦ ĐIỆN TĐ-PX1** | | VN | Tủ | 1 | | | |\n'
        '| + | MCB 1P 10A 6kA | | LS | Cái | 2 | 100 | 200 | Lộ L1 |\n'
        '| 2 | **TỦ ĐIỆN TĐ-PX2** | | VN | Tủ | 1 | | | |\n'
        '| + | MCB 1P 10A 6kA | | LS | Cái | 3 | 100 | 300 | Lộ L1 |'
    )
    assert [(r['panel_code'], r['quantity']) for r in rows if r['row_type'] == 'item'] == [
        ('TĐ-PX1', 2), ('TĐ-PX2', 3)]


def test_saved_iteration_uses_incomer_location_and_ct_context():
    result = _build_analysis_result_schema('00000000-0000-0000-0000-000000000001', 1, [
        dict(category='MCB', name='MCB', panel_code='TĐ-HL.T30', location='Đầu vào tổng', section='Đầu ra'),
        dict(category='METER', name='Đồng hồ ampe', panel_code='TĐ-HL.T30', spec='', quantity=3),
        dict(category='CT', name='Biến dòng', panel_code='TĐ-HL.T30', spec='40/5A', quantity=3),
    ])
    incomer, meter, _ = result.devices
    assert incomer.section == 'Đầu vào'
    assert meter.section == 'Đo lường & Giám sát'
    assert meter.selection_analysis['status'] == 'conditional'
    assert meter.selection_analysis['display_range_a'] == [0, 40]

import json
import asyncio
from functools import wraps
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import HTTPException

from app.services.ai.project_chat import parse_plan, apply_plan, apply_quotation_plan
from app.services.ai.analysis_revision import revise_existing_analysis, quotation_after_device_edit, refresh_linked_quotation_file


def async_test(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


def source_device():
    return dict(category='MCB', name='MCB', tag='Q1', panel_code='P1', quantity=2,
                brand='LS Electric', part_number='LS10', spec='1P 10A 6kA', poles=1, in_a=10, icu_ka=6)


def fake_db(iteration):
    result = MagicMock()
    result.scalar_one_or_none.return_value = iteration
    return SimpleNamespace(execute=AsyncMock(return_value=result), commit=AsyncMock(), rollback=AsyncMock())


def test_nested_edits_keep_other_contactors_and_source_evidence():
    source = dict(name='Sao tam giác', category='STAR_DELTA', quantity=1, source_observations={
        'motor_starter': {'components': [dict(category='CONTACTOR', name=f'KM{i}', quantity=1,
             selected_product={'sku': 'OLD'}) for i in range(3)]}, 'evidence': {'file_id': 7}})
    snapshot = deepcopy(source)
    plan = parse_plan(json.dumps({'reply':'Đổi KM1', 'operations':[{
        'op':'update','index':0,'collection':'components','component_index':1,
        'changes':{'brand':'ABB','part_number':'AX9','quantity':2}}]}))
    edited, = apply_plan([source], plan)
    parts = edited['source_observations']['motor_starter']['components']
    assert parts[1]['quantity'] == 2 and parts[1]['part_number'] == 'AX9'
    assert 'selected_product' not in parts[1]
    assert parts[0] == snapshot['source_observations']['motor_starter']['components'][0]
    assert parts[2] == snapshot['source_observations']['motor_starter']['components'][2]
    assert edited['source_observations']['evidence'] == {'file_id': 7} and source == snapshot


def test_quote_updates_compute_total_without_changing_other_rows():
    rows = [dict(row_type='section_header', name='Thiết bị'),
            dict(row_type='item', sku='A', quantity=2, unit_price=100, line_total=200),
            dict(row_type='item', sku='B', quantity=3, unit_price=50, line_total=150)]
    plan = parse_plan('{"reply":"Sửa giá", "quotation_operations":[{"op":"update","index":1,"changes":{"unit_price":120}}]}')
    updated = apply_quotation_plan(rows, plan)
    assert updated[1]['line_total'] == 240 and updated[2] == rows[2]
    assert rows[1]['unit_price'] == 100
    invalid = parse_plan('{"reply":"Xóa", "quotation_operations":[{"op":"remove","index":0}]}')
    with pytest.raises(ValueError):
        apply_quotation_plan(rows, invalid)


def test_power_update_is_saved_in_circuit_context_without_altering_count():
    plan = parse_plan('{"reply":"Bơm 1 là 2,2 kW", "operations":[{"op":"update","index":0,"changes":{"connected_load":"Bơm 1","power_w":2200}}]}')
    source = source_device()
    edited, = apply_plan([source], plan)
    assert edited['quantity'] == source['quantity']
    assert edited['source_observations']['circuit']['power_w'] == 2200
    assert edited['circuit_context']['power_w'] == 2200 and edited['connected_load'] == 'Bơm 1'


def test_chat_brand_code_replacement_prices_new_maker_while_retaining_detected_source():
    from app.services.ai.procurement_review import build_quotation_rows
    source = {**source_device(), 'brand':'Schneider', 'detected_brand':'Schneider',
        'part_number':'A9F74220', 'in_a':20, 'poles':2, 'icu_ka':None, 'spec':'MCB 2P 20A'}
    plan = parse_plan('{"reply":"Đổi sang LS", "operations":[{"op":"update","index":0,"changes":{"brand":"LS Electric","part_number":"LA63N 2P"}}]}')
    edited, = apply_plan([source],plan)
    assert edited['quantity'] == source['quantity'] and edited['detected_brand'] == 'Schneider'
    assert edited['selection_source'] == 'user_selected'
    catalog = [dict(id='LS-LA63N-2P',brand='LS Electric',sku='LA63N 2P',category='MCB',
        item_name='LA63N 2P',price=268000,specifications={'Số cực':'2P','In (A)':'6-10-16-20-25-32A','Icu(KA)':'6KA'})]
    with patch('app.services.ai.takeoff_pricebook.published_rows',return_value=catalog):
        rows = build_quotation_rows([edited],{},refresh_prices=True)
    row = next(r for r in rows if r.get('source_tags') == ['Q1'])
    assert row['sku'] == 'LA63N 2P' and row['unit_price'] == 268000
    assert row['quantity'] == 2 and row['line_total'] == 536000


def test_explicit_package_price_is_preserved_by_export_normalization():
    from app.services.export.quotation_layout import normalize_quotation_layout
    rows = [dict(row_type='panel_header', id='P1', name='P1'),
            dict(row_type='section_header', name='Vỏ tủ + phụ kiện'),
            dict(row_type='item', name='Nhân công lắp ráp tủ', package_code='LABOR',
                 commercial_package=True, quantity=1, unit_price=100000, line_total=100000, price_status='user_provided')]
    normalized = normalize_quotation_layout(rows)
    labor = next(r for r in normalized if r.get('package_code') == 'LABOR')
    assert labor['unit_price'] == 100000 and labor['line_total'] == 100000


def test_device_quantity_edit_preserves_prices_and_quote_only_rows():
    from app.services.ai.procurement_review import build_quotation_rows
    before = [source_device()]
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[]):
        old = build_quotation_rows(before, {}, refresh_prices=False)
        item = next(r for r in old if r.get('id') == 'P1-device-0')
        item.update(unit_price=900, line_total=1800, price_status='user_provided')
        old.append(dict(id='custom', row_type='item', category='CUSTOM', name='Kiểm định bổ sung',
                        sku='CUSTOM', quantity=1, unit_price=500, line_total=500))
        after = [{**before[0], 'quantity':3}]
        updated = quotation_after_device_edit(before, after, old)
    item = next(r for r in updated if r.get('id') == 'P1-device-0')
    assert item['quantity'] == 3 and item['unit_price'] == 900 and item['line_total'] == 2700
    assert next(r for r in updated if r.get('id') == 'custom')['line_total'] == 500


def test_negotiated_prices_for_identical_codes_stay_separate_after_edit():
    from app.services.ai.procurement_review import build_quotation_rows
    before = [source_device(), {**source_device(), 'tag':'Q2'}]
    with patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[]):
        rows = build_quotation_rows(before[:1], {}, refresh_prices=False)
        first = next(r for r in rows if r.get('id') == 'P1-device-0')
        first.update(unit_price=900, line_total=1800, source_tags=['Q1'])
        rows.append({**deepcopy(first), 'id':'P1-device-1','unit_price':800,'line_total':1600,'source_tags':['Q2']})
        after = [{**before[0],'quantity':3},before[1]]
        updated = quotation_after_device_edit(before,after,rows)
    items = [r for r in updated if r.get('category') == 'MCB']
    assert [(r['source_tags'],r['unit_price'],r['line_total']) for r in items] == [(['Q1'],900,2700),(['Q2'],800,1600)]


@async_test
async def test_revision_saves_same_iteration_and_rebuilds_quote():
    iteration = SimpleNamespace(id=7, iteration_number=4, session_id='session',
        ai_parsed_devices=[source_device()], devices_after_validation=[source_device()],
        confidence_scores={}, user_corrections={})
    db = fake_db(iteration)
    response = '{"reply":"Đã sửa số lượng Q1 thành 3", "operations":[{"op":"update","index":0,"changes":{"quantity":3}}]}'
    with patch('app.services.ai.analysis_revision.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[1])), \
         patch('app.services.ai.analysis_revision.ConnectionPoolService.call_with_fallback', AsyncMock(return_value=(response,None))), \
         patch('app.services.ai.takeoff_pricebook.published_rows', return_value=[]):
        result = await revise_existing_analysis(db,1,1,7,'Sửa số lượng Q1 thành 3')
    assert result['updated_in_place'] and result['iteration_id'] == 7 and iteration.iteration_number == 4
    assert iteration.ai_parsed_devices[0]['quantity'] == 3
    assert next(r for r in result['quotation_rows'] if r.get('source_tags') == ['Q1'])['quantity'] == 3
    db.commit.assert_awaited_once()


@async_test
async def test_question_has_no_write_and_foreign_result_is_rejected():
    iteration = SimpleNamespace(id=7, iteration_number=4, session_id='session',
        ai_parsed_devices=[source_device()], devices_after_validation=[source_device()],
        confidence_scores={}, user_corrections={})
    db = fake_db(iteration)
    with patch('app.services.ai.analysis_revision.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[1])), \
         patch('app.services.ai.analysis_revision.ConnectionPoolService.call_with_fallback', AsyncMock(return_value=('{"reply":"Q1 có 2 thiết bị"}',None))):
        result = await revise_existing_analysis(db,1,1,7,'Q1 có bao nhiêu thiết bị?')
    assert result['action_type'] == 'general_chat'
    db.commit.assert_not_awaited()
    with pytest.raises(HTTPException) as failure:
        await revise_existing_analysis(fake_db(None),1,1,8,'Sửa')
    assert failure.value.status_code == 404


@async_test
async def test_existing_generated_workbook_keeps_identity_and_path(tmp_path):
    from openpyxl import Workbook, load_workbook
    target, generated = tmp_path/'old.xlsx', tmp_path/'new.xlsx'
    for path, amount in [(target,2),(generated,3)]:
        workbook = Workbook(); workbook.active['A1']=amount; workbook.save(path)
    file = SimpleNamespace(id=5, project_id=1, filename='old.xlsx', file_path=str(target), file_size=target.stat().st_size)
    db = fake_db(file)
    with patch('app.services.export.quotation_exporter.QuotationExporterService.export', return_value=str(generated)):
        backup = await refresh_linked_quotation_file(db,1,{'quotation_file_id':5},[])
    assert file.id == 5 and file.file_path == str(target)
    workbook = load_workbook(target); assert workbook.active['A1'].value == 3; workbook.close()
    assert backup[0] == target and backup[1] and not generated.exists()


@async_test
async def test_revision_intent_uses_existing_result_without_source_discovery():
    from app.api.v1.endpoints import el_agent
    payload = SimpleNamespace(project_id=1, message='Sửa số lượng Q1 thành 3',
        context={'iteration_id':7,'file_ids':[9],'takeoff_scope':[{'scope_token':'expired'}]})
    with patch.object(el_agent, 'owned_project', AsyncMock()), \
         patch('app.services.ai.el_conversation.resolve_request', AsyncMock(return_value={
             'original':payload.message,'effective':payload.message,'intent':'takeoff_update'})), \
         patch('app.services.ai.analysis_revision.revise_existing_analysis', AsyncMock(return_value={'reply':'Đã sửa','updated_in_place':True})) as revise, \
         patch('app.services.ai.takeoff_regions.discover_panels', AsyncMock()) as discover:
        result = await el_agent.next_action(payload,None,None,SimpleNamespace(id=1))
    assert result['updated_in_place'] is True
    assert revise.await_args.args[3] == 7
    discover.assert_not_awaited()


@async_test
async def test_retry_does_not_apply_same_revision_twice():
    iteration = SimpleNamespace(id=7,iteration_number=4,session_id='session',
        ai_parsed_devices=[source_device()],devices_after_validation=[source_device()],
        confidence_scores={},user_corrections={'revision_history':[{
            'request_key':'same-request','reply':'Đã sửa','device_changed':True}]})
    db = fake_db(iteration)
    with patch('app.services.ai.analysis_revision.ConnectionPoolService.call_with_fallback', AsyncMock()) as ai:
        result = await revise_existing_analysis(db,1,1,7,'Tăng thêm 2',{'request_id':'same-request'})
    assert result['iteration_id'] == 7
    ai.assert_not_awaited()
    db.commit.assert_not_awaited()


@async_test
async def test_database_and_linked_excel_are_updated_in_place_for_takeoff_and_price_edits(tmp_path):
    from openpyxl import Workbook, load_workbook
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.models import Base, User, Project, ConversationSession, AnalysisIteration
    from app.models.project_file import ProjectFile
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as db:
            user = User(email='revision@test.example', hashed_password='unused'); db.add(user); await db.flush()
            project = Project(user_id=user.id,name='Revision'); db.add(project); await db.flush()
            session = ConversationSession(user_id=user.id,project_id=project.id,total_iterations=1); db.add(session); await db.flush()
            target = tmp_path/'existing.xlsx'
            book = Workbook(); book.active['A1']=2; book.save(target)
            file = ProjectFile(project_id=project.id,filename='existing.xlsx',file_path=str(target),
                file_type='xlsx',file_size=target.stat().st_size,is_generated=True)
            db.add(file); await db.flush()
            iteration = AnalysisIteration(session_id=session.id,iteration_number=1,trigger_type='el_takeoff',
                status='completed',ai_parsed_devices=[source_device()],devices_after_validation=[source_device()],
                confidence_scores={'quotation_file_id':file.id},user_corrections={})
            db.add(iteration); await db.commit()
            original_id, file_id = iteration.id, file.id
            responses = [('{"reply":"Sửa Q1 thành 3", "operations":[{"op":"update","index":0,"changes":{"quantity":3}}]}',None)]
            def export(**kwargs):
                row = next(r for r in kwargs['devices'] if r.get('source_tags') == ['Q1'])
                workbook = Workbook(); workbook.active['A1']=row['quantity']; workbook.active['B1']=row.get('line_total')
                output = tmp_path/'generated.xlsx'; workbook.save(output); return str(output)
            with patch('app.services.ai.analysis_revision.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[1])), \
                 patch('app.services.ai.analysis_revision.ConnectionPoolService.call_with_fallback', AsyncMock(side_effect=responses)), \
                 patch('app.services.ai.takeoff_pricebook.published_rows',return_value=[]), \
                 patch('app.services.export.quotation_exporter.QuotationExporterService.export', side_effect=export):
                result = await revise_existing_analysis(db,project.id,user.id,original_id,'Sửa Q1 thành 3',{'request_id':'count'})
            index = next(i for i,r in enumerate(result['quotation_rows']) if r.get('source_tags') == ['Q1'])
            response = json.dumps({'reply':'Sửa giá Q1 thành 120', 'quotation_operations':[{'op':'update','index':index,'changes':{'unit_price':120}}]})
            with patch('app.services.ai.analysis_revision.ConnectionPoolService.get_ordered_connections', AsyncMock(return_value=[1])), \
                 patch('app.services.ai.analysis_revision.ConnectionPoolService.call_with_fallback', AsyncMock(return_value=(response,None))), \
                 patch('app.services.export.quotation_exporter.QuotationExporterService.export',side_effect=export):
                quoted = await revise_existing_analysis(db,project.id,user.id,original_id,'Sửa giá Q1 thành 120',{'request_id':'price'})
            assert quoted['iteration_id'] == original_id and quoted['action_type'] == 'update_quotation'
            assert (await db.scalar(select(func.count()).select_from(AnalysisIteration))) == 1
            assert (await db.scalar(select(func.count()).select_from(ProjectFile))) == 1
            await db.refresh(iteration); await db.refresh(file)
            assert iteration.ai_parsed_devices[0]['quantity'] == 3
            assert file.id == file_id and file.file_path == str(target)
            workbook = load_workbook(target)
            assert workbook.active['A1'].value == 3 and workbook.active['B1'].value == 360
            workbook.close()
    finally:
        await engine.dispose()

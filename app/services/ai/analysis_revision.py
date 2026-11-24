"""Apply conversational edits to the existing takeoff and its quotation."""
import asyncio
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import tempfile

from fastapi import HTTPException
from sqlalchemy import select, update, text
from app.models.analysis_iteration import AnalysisIteration
from app.models.conversation_session import ConversationSession
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.services.ai.project_chat import (
    conversation_prompt, parse_plan, apply_plan, apply_quotation_plan, updated_confidence,
)
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService


def quotation_after_device_edit(before, after, previous, panels=None):
    from app.services.ai.procurement_review import build_quotation_rows
    old_source = build_quotation_rows(before, {}, panels, refresh_prices=False)
    fresh = build_quotation_rows(after, {}, panels, refresh_prices=True)

    def indexed(rows):
        panel, section = '', ''
        for row in rows:
            if row.get('row_type') == 'panel_header':
                panel = row.get('panel_code') or row.get('name') or ''
            elif row.get('row_type') == 'section_header':
                section = row.get('name') or ''
            yield panel, section, row

    def key(panel, row):
        return (panel, row.get('package_code'), row.get('category'), row.get('sku') or '',
                row.get('origin') or '', row.get('spec') or '', row.get('unit') or '',
                row.get('name') if not row.get('sku') else '', row.get('assembly_proposal_key'))

    old = {}
    for panel, _, row in indexed(previous):
        if row.get('row_type') in {'item', 'accessory'}:
            old.setdefault(key(panel, row), []).append(row)
    source_keys = {key(panel, row) for panel, _, row in indexed(old_source)}
    # Preserve per-circuit negotiated prices when the fresh catalog would merge
    # equal SKUs back into one row.
    expanded = []
    for panel, _, row in indexed(fresh):
        tags = set(row.get('source_tags') or [])
        matches = old.get(key(panel, row), [])
        tagged = [r for r in matches if tags.intersection(r.get('source_tags') or [])]
        if len(tags) > 1 and len({r.get('unit_price') for r in tagged}) > 1:
            remaining = set(tags)
            for index, prior in enumerate(tagged):
                subset = remaining.intersection(prior.get('source_tags') or [])
                if not subset:
                    continue
                quantities = [d.get('procurement_quantity', d.get('quantity')) for d in after
                              if d.get('panel_code') == panel and d.get('tag') in subset]
                if len(quantities) != len(subset) or any(q is None for q in quantities):
                    continue
                part = {**deepcopy(row), 'id': f'{row["id"]}-price-{index}',
                        'source_tags': sorted(subset), 'quantity': sum(quantities)}
                expanded.append(part)
                remaining -= subset
            if remaining:
                part = deepcopy(row)
                part['source_tags'] = sorted(remaining)
                part['quantity'] = sum(d.get('quantity') or 0 for d in after
                                       if d.get('panel_code') == panel and d.get('tag') in remaining)
                expanded.append(part)
        else:
            expanded.append(row)
    fresh = expanded
    fresh_keys = set()
    for panel, _, row in indexed(fresh):
        identity = key(panel, row)
        fresh_keys.add(identity)
        matches = old.get(identity, [])
        if not matches or row.get('row_type') not in {'item', 'accessory'}:
            continue
        tags = set(row.get('source_tags') or [])
        previous_row = next((r for r in matches if tags and tags == set(r.get('source_tags') or [])), matches[0])
        if row.get('commercial_package'):
            row.update({k: deepcopy(v) for k, v in previous_row.items() if k != 'id'})
        elif row.get('pricing_basis') != 'selected_components':
            price = previous_row.get('unit_price')
            row.update(unit_price=price, line_total=price * row['quantity']
                       if price is not None and row.get('quantity') is not None else None,
                       notes=previous_row.get('notes') or '',
                       price_status=previous_row.get('price_status') or 'pending')
    # Keep quote-only labor/custom rows; source rows removed by the user stay removed.
    extras = {}
    for panel, section, row in indexed(previous):
        identity = key(panel, row)
        if (row.get('row_type') in {'item', 'accessory'} and identity not in fresh_keys | source_keys
                and not row.get('assembly_proposal_key') and not row.get('source_tags')
                and '-device-' not in str(row.get('id') or '')):
            extras.setdefault(panel, []).append((section, deepcopy(row)))
    result, active_panel = [], ''
    def flush_extra():
        for section, row in extras.pop(active_panel, []):
            result.extend([dict(row_type='section_header', name=section or 'Bổ sung báo giá'), row])
    for row in fresh:
        if row.get('row_type') == 'panel_header':
            flush_extra()
            active_panel = row.get('panel_code') or row.get('name') or ''
        result.append(row)
    flush_extra()
    return result


async def refresh_linked_quotation_file(db, project_id, scores, rows):
    """Replace an owned generated workbook in place, retaining its file identity."""
    reference = scores.get('quotation_file') or (scores.get('design_result') or {}).get('quotation_file') or {}
    file_id = scores.get('quotation_file_id') or (reference.get('id') if isinstance(reference, dict) else None)
    if not file_id:
        return None
    file = (await db.execute(select(ProjectFile).where(ProjectFile.id == file_id,
        ProjectFile.project_id == project_id, ProjectFile.is_generated.is_(True)))).scalar_one_or_none()
    if file is None or Path(file.filename).suffix.lower() != '.xlsx':
        raise HTTPException(409, 'File báo giá đã liên kết không còn khả dụng để cập nhật.')
    from app.services.export.quotation_exporter import QuotationExporterService
    target = Path(file.file_path).resolve()
    original = target.read_bytes() if target.exists() else None
    generated = await asyncio.to_thread(QuotationExporterService.export, devices=rows,
        project_name=target.stem, brand_preference='Theo lựa chọn thiết bị')
    generated = Path(generated).resolve()
    staged = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.xlsx', delete=False) as temp:
            staged = Path(temp.name)
        shutil.copyfile(generated, staged)
        os.replace(staged, target)
        file.file_size = target.stat().st_size
    finally:
        if staged and staged.exists():
            staged.unlink()
        if generated != target and generated.exists():
            generated.unlink()
    return target, original


def _fingerprint(iteration):
    data = [iteration.devices_after_validation or iteration.ai_parsed_devices or [],
            iteration.confidence_scores or {}]
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


async def revise_existing_analysis(db, project_id, user_id, iteration_id, message, context=None):
    if type(iteration_id) is not int or iteration_id <= 0:
        raise HTTPException(422, 'Cần chọn kết quả bóc tách hoặc báo giá cần sửa.')
    query = select(AnalysisIteration).join(ConversationSession,
        ConversationSession.id == AnalysisIteration.session_id).where(
        AnalysisIteration.id == iteration_id, ConversationSession.project_id == project_id,
        ConversationSession.user_id == user_id)
    iteration = (await db.execute(query)).scalar_one_or_none()
    if iteration is None:
        raise HTTPException(404, 'Không tìm thấy kết quả trong dự án này.')
    request_key = (context or {}).get('request_id') or (context or {}).get('run_id')
    for revision in (iteration.user_corrections or {}).get('revision_history') or []:
        if request_key and revision.get('request_key') == str(request_key):
            return {'reply': revision.get('reply') or 'Đã cập nhật kết quả hiện có.',
                'action_type': 'update_devices' if revision.get('device_changed') else 'update_quotation',
                'updated_in_place': True, 'project_id': project_id, 'base_iteration_id': iteration_id,
                'iteration_id': iteration_id, 'iteration_number': iteration.iteration_number,
                'session_id': str(iteration.session_id),
                'devices': iteration.devices_after_validation or iteration.ai_parsed_devices or [],
                'quotation_rows': (iteration.confidence_scores or {}).get('quotation_rows') or []}
    fingerprint = _fingerprint(iteration)
    before = deepcopy(iteration.devices_after_validation or iteration.ai_parsed_devices or [])
    scores = deepcopy(iteration.confidence_scores or {})
    previous_rows = scores.get('quotation_rows') or []
    connections = await ConnectionPoolService.get_ordered_connections(db)
    if not connections:
        raise HTTPException(503, 'Chưa có kết nối AI khả dụng.')
    prompt = conversation_prompt(message, before, {**(context or {}), 'mode': 'revision', 'quotation_rows': previous_rows})
    raw, _ = await ConnectionPoolService.call_with_fallback(db=db, connections=connections,
        call_fn=VisionAnalyzerService.analyze_text, prompt=prompt)
    try:
        plan = parse_plan(raw)
        after = apply_plan(before, plan)
        quote = apply_quotation_plan(previous_rows, plan)
    except (ValueError, TypeError, KeyError, IndexError) as error:
        raise HTTPException(502, 'AI trả về chỉnh sửa chưa hợp lệ; kết quả hiện tại được giữ nguyên.') from error
    changed = after != before
    if not changed and quote == previous_rows:
        return {'reply': plan.reply, 'action_type': 'general_chat'}
    if changed:
        from app.services.ai.motor_starter_context import enrich_motor_starters
        enrich_motor_starters(after)
        quote = await asyncio.to_thread(quotation_after_device_edit, before, after, quote, scores.get('panels'))
    # Lock and re-read after the model call, so a stale chat cannot overwrite another edit.
    if getattr(getattr(db, 'bind', None), 'dialect', None) is not None and db.bind.dialect.name == 'sqlite':
        await db.commit()
        await db.execute(text('BEGIN IMMEDIATE'))
    current = (await db.execute(query.with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()
    if current is None or _fingerprint(current) != fingerprint:
        raise HTTPException(409, 'Kết quả vừa thay đổi ở lượt khác; hãy gửi lại yêu cầu trên bản mới nhất.')
    new_scores = updated_confidence(scores, after) if changed else deepcopy(scores)
    for key in ('quotation_file_id', 'quotation_file'):
        if key in scores:
            new_scores[key] = deepcopy(scores[key])
    linked_quote = (scores.get('design_result') or {}).get('quotation_file')
    if linked_quote and 'quotation_file' not in new_scores:
        new_scores['quotation_file'] = deepcopy(linked_quote)
    new_scores['quotation_rows'] = quote
    current.ai_parsed_devices = after
    current.devices_after_validation = after
    current.confidence_scores = new_scores
    now = datetime.now(timezone.utc)
    corrections = deepcopy(current.user_corrections or {})
    journal = list(corrections.get('revision_history') or [])
    journal.append({'at': now.isoformat(), 'request': message, 'operations': plan.model_dump(exclude_none=True),
                    'request_key': str(request_key) if request_key else None, 'reply': plan.reply, 'device_changed': changed})
    current.user_corrections = {**corrections, 'revision_history': journal[-20:], 'reply': plan.reply}
    backup = None
    try:
        backup = await refresh_linked_quotation_file(db, project_id, scores, quote)
        await db.execute(update(Project).where(Project.id == project_id).values(updated_at=now))
        await db.commit()
    except Exception:
        await db.rollback()
        if backup:
            if backup[1] is not None:
                backup[0].write_bytes(backup[1])
            elif backup[0].exists():
                backup[0].unlink()
        raise
    return {'reply': plan.reply + '\n\nĐã cập nhật trực tiếp kết quả hiện có và bảng báo giá.',
        'action_type': 'update_devices' if changed else 'update_quotation', 'updated_in_place': True,
        'project_id': project_id, 'base_iteration_id': iteration_id, 'iteration_id': current.id,
        'iteration_number': current.iteration_number, 'session_id': str(current.session_id),
        'devices': after, 'quotation_rows': quote}

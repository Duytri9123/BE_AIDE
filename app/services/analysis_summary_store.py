"""Maintain history metadata in the same transaction as its source iteration."""
from sqlalchemy import delete, event, inspect, select, update

from app.models.analysis_iteration import AnalysisIteration
from app.models.analysis_summary import AnalysisSummary
from app.models.analysis_payload import AnalysisPayload

METADATA = ('id', 'session_id', 'iteration_number', 'trigger_type', 'user_message',
            'files_analyzed', 'created_at', 'updated_at', 'status')
PAYLOAD = ('ai_parsed_devices', 'devices_after_validation', 'confidence_scores')


def without_images(value):
    if isinstance(value, dict):
        return {key: without_images(item) for key, item in value.items()
                if key not in {'evidence_image', 'evidence_images', 'panel_evidence_image',
                               'panel_images', 'evidence_overviews'}}
    if isinstance(value, list):
        return [without_images(item) for item in value]
    if isinstance(value, str) and value.startswith('data:image/'):
        return None
    return value


def summary_values(source):
    raw = source.get('devices_after_validation') or source.get('ai_parsed_devices') or []
    raw = raw if isinstance(raw, list) else []
    conf = source.get('confidence_scores') or {}
    conf = conf if isinstance(conf, dict) else {}
    values = {key: source[key] for key in METADATA}
    values['updated_at'] = values['updated_at'] or values['created_at']
    values['has_devices'] = bool(source.get('ai_parsed_devices'))
    values['display_devices'] = without_images(raw)
    values['devices'] = [{key: d.get(key) for key in
                         ('panel_code', 'panel_name', 'quantity', 'source_filename')}
                        for d in raw if isinstance(d, dict)]
    values['confidence'] = {key: conf.get(key) for key in
                            ('panel_code', 'panel_name', 'panel_info', 'quotation_file_id', 'report_file_id')}
    values['confidence'].update(quotation_count=len(conf.get('quotation_rows') or []),
                                design_result=bool(conf.get('design_result')))
    return values


def replace_summary(connection, values, payload=None):
    table = AnalysisSummary.__table__
    connection.execute(delete(table).where(table.c.id == values['id']))
    connection.execute(table.insert().values(**values))
    if payload is not None:
        connection.execute(delete(AnalysisPayload).where(AnalysisPayload.id == values['id']))
        connection.execute(AnalysisPayload.__table__.insert().values(
            id=values['id'], updated_at=values['updated_at'], payload=payload))
    else:
        connection.execute(update(AnalysisPayload).where(AnalysisPayload.id == values['id'])
                           .values(updated_at=values['updated_at']))


def sync_iteration(mapper, connection, target):
    state = inspect(target)
    # Metadata-only updates reuse the compact payload, including deferred loads.
    existing = None
    if not any(state.attrs[key].history.has_changes() for key in PAYLOAD):
        existing = connection.execute(select(AnalysisSummary.__table__).where(
            AnalysisSummary.id == target.id)).mappings().first()
    keys = METADATA if existing else METADATA + PAYLOAD
    source = {key: target.__dict__[key] for key in keys if key in target.__dict__}
    missing = [key for key in keys if key not in source]
    if missing:
        row = connection.execute(select(*(getattr(AnalysisIteration, key) for key in missing))
                                 .where(AnalysisIteration.id == target.id)).mappings().one()
        source.update(row)
    if existing:
        values = dict(existing)
        values.update(source)
    else:
        values = summary_values(source)
    from app.services.analysis_payloads import pack_payload
    replace_summary(connection, values, None if existing else pack_payload(source))


def install_summary_events():
    for name in ('after_insert', 'after_update'):
        if not event.contains(AnalysisIteration, name, sync_iteration):
            event.listen(AnalysisIteration, name, sync_iteration)

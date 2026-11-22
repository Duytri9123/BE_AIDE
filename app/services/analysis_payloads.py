"""Losslessly deduplicate inline images and compress saved result read copies."""
import asyncio
import hashlib
import json
import logging
import zlib

from sqlalchemy import select
from app.models.analysis_payload import AnalysisPayload
from app.models.analysis_iteration import AnalysisIteration
from app.models.analysis_summary import AnalysisSummary


def pack_payload(source):
    images, references, by_digest = [], [], {}
    def compact(value, path):
        if isinstance(value, str) and value.startswith('data:image/'):
            digest = hashlib.sha256(value.encode()).digest()
            if digest not in by_digest:
                by_digest[digest] = len(images)
                images.append(value)
            references.append([path, by_digest[digest]])
            return None
        if isinstance(value, dict):
            return {key: compact(item, path + [key]) for key, item in value.items()}
        if isinstance(value, list):
            return [compact(item, path + [index]) for index, item in enumerate(value)]
        return value
    parsed = source.get('ai_parsed_devices')
    validated = source.get('devices_after_validation')
    same = parsed == validated
    data = compact({'ai_parsed_devices': parsed,
                    'devices_after_validation': None if same else validated,
                    'confidence_scores': source.get('confidence_scores')}, [])
    packed = {'version': 1, 'data': data, 'images': images, 'references': references, 'validated_same': same}
    return zlib.compress(json.dumps(packed, ensure_ascii=False, separators=(',', ':')).encode(), level=3)


def unpack_payload(blob):
    packed = json.loads(zlib.decompress(blob))
    if packed['version'] != 1:
        raise ValueError('Unsupported analysis read payload version')
    data = packed['data']
    for path, index in packed['references']:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = packed['images'][index]
    if packed['validated_same']:
        data['devices_after_validation'] = data['ai_parsed_devices']
    return data


async def saved_iteration(db, iteration_id):
    row = (await db.execute(select(AnalysisSummary.id, AnalysisSummary.session_id,
        AnalysisSummary.iteration_number, AnalysisPayload.payload)
        .join(AnalysisPayload, AnalysisSummary.id == AnalysisPayload.id)
        .where(AnalysisSummary.id == iteration_id,
               AnalysisPayload.updated_at == AnalysisSummary.updated_at))).first()
    data = None
    if row is not None:
        try:
            data = await asyncio.to_thread(unpack_payload, row.payload)
        except (ValueError, zlib.error, KeyError, IndexError, TypeError):
            logging.getLogger(__name__).warning('Invalid analysis read copy; using source id=%s', iteration_id)
    if data is None:
        # Compatibility during a staged backfill: retain access to the source.
        from sqlalchemy.orm import load_only
        return (await db.execute(select(AnalysisIteration).where(AnalysisIteration.id == iteration_id)
            .options(load_only(AnalysisIteration.id, AnalysisIteration.session_id,
                AnalysisIteration.iteration_number, AnalysisIteration.ai_parsed_devices,
                AnalysisIteration.devices_after_validation, AnalysisIteration.confidence_scores)))).scalar_one_or_none()
    return AnalysisIteration(id=row.id, session_id=row.session_id,
                             iteration_number=row.iteration_number, **data)

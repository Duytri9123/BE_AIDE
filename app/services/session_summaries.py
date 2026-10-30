"""Small revision-keyed history cache; source iterations remain authoritative."""
import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path

from sqlalchemy import select, cast, String
from app.models.analysis_iteration import AnalysisIteration


def summarize(devices, confidence):
    devices = devices if isinstance(devices, list) else []
    confidence = confidence if isinstance(confidence, dict) else {}
    return {'devices': [{key: device.get(key) for key in ('panel_code','panel_name','quantity')}
                        for device in devices if isinstance(device, dict)],
            'conf': {key: confidence.get(key) for key in ('panel_code','panel_name','panel_info')}}


def read_summary(path, revision):
    try:
        cached = json.loads(path.read_text(encoding='utf-8'))
        if cached.get('revision') == revision:
            return cached['summary']
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def write_summary(path, revision, summary):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
            temporary = file.name
            json.dump({'revision':revision,'summary':summary}, file, ensure_ascii=False)
        os.replace(temporary, path)
    except OSError:
        pass  # Cache failure must never hide a saved session.
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


async def get_summary(db, row):
    database = Path(db.bind.url.database).resolve()
    namespace = hashlib.sha256(str(database).encode()).hexdigest()[:16]
    path = database.parent/'tmp'/'session-summaries'/namespace/f'{row.id}.json'
    revision = str(row.updated_at or row.created_at)
    cached = await asyncio.to_thread(read_summary, path, revision)
    if cached is not None:
        return cached
    # Decode only one missing revision at a time, off the HTTP event loop.
    raw = (await db.execute(select(cast(AnalysisIteration.ai_parsed_devices, String),
                                   cast(AnalysisIteration.confidence_scores, String))
                            .where(AnalysisIteration.id == row.id))).one()
    def decode():
        return summarize(json.loads(raw[0] or 'null'), json.loads(raw[1] or 'null'))
    summary = await asyncio.to_thread(decode)
    await asyncio.to_thread(write_summary, path, revision, summary)
    return summary

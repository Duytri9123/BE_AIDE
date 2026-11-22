"""Build resumable compact history rows without changing saved results.

Run after ``alembic upgrade head`` and before starting the new API/workers.
Each source row is read separately; existing up-to-date rows are skipped.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from app.core.config import settings
from app.models.analysis_iteration import AnalysisIteration
from app.models.analysis_summary import AnalysisSummary
from app.models.analysis_payload import AnalysisPayload
from app.services.analysis_payloads import pack_payload
from app.services.analysis_summary_store import METADATA, PAYLOAD, replace_summary, summary_values


def main():
    url = settings.DATABASE_ASYNC_URL.replace('sqlite+aiosqlite:', 'sqlite:')
    engine = create_engine(url, connect_args={'timeout': 60} if url.startswith('sqlite:') else {})
    started = time.perf_counter()
    changed = 0
    with engine.connect() as connection:
        ids = list(connection.execute(select(AnalysisIteration.id).order_by(AnalysisIteration.id.desc())).scalars())
    for index, iteration_id in enumerate(ids):
        with engine.connect() as connection:
            revision = connection.execute(select(AnalysisIteration.updated_at)
                .where(AnalysisIteration.id == iteration_id)).scalar_one_or_none()
            cached = connection.execute(select(AnalysisSummary.updated_at)
                .where(AnalysisSummary.id == iteration_id)).scalar_one_or_none()
            packed_revision = connection.execute(select(AnalysisPayload.updated_at)
                .where(AnalysisPayload.id == iteration_id)).scalar_one_or_none()
            if revision is None or revision == cached == packed_revision:
                continue
            row = connection.execute(select(*(getattr(AnalysisIteration, key) for key in METADATA + PAYLOAD))
                .where(AnalysisIteration.id == iteration_id)).mappings().one_or_none()
            if row is None:
                continue
            values = summary_values(row)
            payload = pack_payload(row)
        with engine.begin() as connection:
            # Serialize the revision check and upsert with normal SQLite writers.
            if engine.dialect.name == 'sqlite':
                connection.exec_driver_sql('BEGIN IMMEDIATE')
            current = connection.execute(select(AnalysisIteration.updated_at)
                .where(AnalysisIteration.id == iteration_id)).scalar_one_or_none()
            if current != values['updated_at']:
                continue  # A concurrent edit will be picked up on the next run.
            replace_summary(connection, values, payload)
            changed += 1
        print(json.dumps({'row': index + 1, 'total': len(ids), 'id': iteration_id,
                          'elapsed_s': round(time.perf_counter()-started, 2)}), flush=True)
    engine.dispose()
    print(json.dumps({'updated': changed, 'total': len(ids),
                      'seconds': round(time.perf_counter()-started, 2)}), flush=True)


if __name__ == '__main__':
    main()

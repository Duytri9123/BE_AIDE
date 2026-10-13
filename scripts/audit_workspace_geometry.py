"""Read a workspace's latest takeoff and audit automatic CAD matching."""
import asyncio
import json
from pathlib import Path
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine
from app.models.analysis_iteration import AnalysisIteration
from app.models.conversation_session import ConversationSession
from app.services.cad.automatic_selection import select_device_geometry
from app.services.ai.auxiliary_devices import expand_devices


async def main():
    async with AsyncSessionLocal() as db:
        iteration = (await db.execute(select(AnalysisIteration).join(ConversationSession)
            .where(ConversationSession.project_id == 16)
            .order_by(AnalysisIteration.created_at.desc()).limit(1))).scalar_one()
        payload = iteration.devices_after_validation or iteration.ai_parsed_devices
        rows = payload if isinstance(payload, list) else (payload or {}).get('devices', [])
        result = [select_device_geometry(d) for d in expand_devices(rows)]
        folder = Path(__file__).resolve().parents[2] / 'outputs/workspace-457-e2e'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'automatic-geometry-audit.json').write_text(json.dumps({
            'iteration_id': iteration.id, 'devices': result}, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps({'iteration_id': iteration.id, 'rows': len(rows),
            'expanded_rows': len(result), 'selected': sum(bool((r.get('cad') or {}).get('asset_id')) for r in result),
            'unresolved': [{'tag': r.get('tag'), 'name': r.get('name'), 'category': r.get('category'),
                'reason': ((r.get('cad') or {}).get('automatic_selection') or {}).get('reason')} for r in result
                if not (r.get('cad') or {}).get('asset_id')]}, ensure_ascii=True))
    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())

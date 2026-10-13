"""Read-only source quotation reconciliation for the current workspace."""
import asyncio
import json
from collections import Counter
from pathlib import Path
from sqlalchemy import select
from app.db.session import AsyncSessionLocal, engine
from app.models.analysis_iteration import AnalysisIteration
from app.models.conversation_session import ConversationSession
from app.services.ai.quotation_configuration import read_configuration, apply_configuration


async def main():
    quote=next(Path('C:/Users/admin/Downloads').glob('Đơn 457.*bg*Toxcom*.xlsx'))
    config=read_configuration(quote)
    async with AsyncSessionLocal() as db:
        it=(await db.execute(select(AnalysisIteration).join(ConversationSession)
            .where(ConversationSession.project_id==16)
            .order_by(AnalysisIteration.created_at.desc(),AnalysisIteration.id.desc()).limit(1))).scalar_one()
        rows=apply_configuration(it.ai_parsed_devices,config)
        stored_source_quantity=sum(int(d.get('quantity') or 1) for d in it.ai_parsed_devices)
        stored_config=it.confidence_scores or {}
        stored_design_quantity=sum(int(d.get('quantity') or 1) for d in stored_config.get('design_devices',[]))
    count=Counter()
    for d in rows: count[(d['panel_code'],d['category'])]+=d['quantity']
    reruns=[]
    for panel in {d['panel_code'] for d in rows}:
        group=[d for d in rows if d['panel_code']==panel]
        again=apply_configuration(group,config)
        reruns.append({'panel':panel,'input_quantity':sum(d['quantity'] for d in group),
                       'output_quantity':sum(d['quantity'] for d in again),
                       'source_panels':list({d.get('source_observations',{}).get('schematic',{}).get('device',{}).get('panel_code') for d in group})})
    folder=Path(__file__).resolve().parents[2]/'outputs/workspace-457-e2e'
    report={'iteration_id':it.id,'configuration':config,'devices':rows,
            'stored_source_quantity':stored_source_quantity,'stored_design_quantity':stored_design_quantity,
            'quantity':sum(count.values()),'counts':[{'panel':p,'category':c,'quantity':n} for (p,c),n in count.items()]}
    (folder/'approved-quotation-configuration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'quantity':report['quantity'],'counts':report['counts'],
                     'stored_source_quantity':stored_source_quantity,'stored_design_quantity':stored_design_quantity,
                     'package_prices':[p.get('package_price_vnd') for p in config['panels']], 'reruns':reruns},ensure_ascii=True))
    await engine.dispose()


if __name__=='__main__': asyncio.run(main())

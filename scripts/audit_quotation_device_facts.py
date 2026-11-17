"""Read-only audit of saved takeoffs/quotations. Never reprices or rewrites history."""
import asyncio
import json
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.services.ai.device_facts import enrich_device_facts, enrich_quotation_facts
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():
    stats=Counter(); revisions=[]
    engine=create_async_engine(settings.DATABASE_ASYNC_URL, echo=False)
    async with engine.connect() as connection:
        if connection.dialect.name == 'sqlite':
            # Do not load embedded drawing images or full conversation payloads.
            sql="SELECT id, (SELECT json_group_array(json_remove(d.value,'$.evidence_image','$.panel_evidence_image','$.evidence_images','$.source_observations.schematic.device.evidence_image','$.source_observations.schematic.device.panel_evidence_image')) FROM json_each(CASE WHEN json_type(ai_parsed_devices)='array' THEN ai_parsed_devices ELSE '[]' END) d) AS ai_parsed_devices, json_extract(confidence_scores,'$.quotation_rows','$.quotation_rows_by_panel') AS confidence_scores FROM analysis_iterations"
        else:
            sql="SELECT id, (SELECT jsonb_agg(d.value - 'evidence_image' - 'panel_evidence_image' - 'evidence_images') FROM jsonb_array_elements(CASE WHEN jsonb_typeof(ai_parsed_devices::jsonb)='array' THEN ai_parsed_devices::jsonb ELSE '[]'::jsonb END) d) AS ai_parsed_devices, jsonb_build_object('quotation_rows',confidence_scores::jsonb->'quotation_rows','quotation_rows_by_panel',confidence_scores::jsonb->'quotation_rows_by_panel') AS confidence_scores FROM analysis_iterations"
        stream=await connection.stream(text(sql))
        async for item in stream.mappings():
            stats['iterations']+=1
            def decode(value):
                return json.loads(value) if isinstance(value,str) else value
            devices=decode(item['ai_parsed_devices']) or []
            conf=decode(item['confidence_scores']) or {}
            if isinstance(conf,list):conf=dict(zip(('quotation_rows','quotation_rows_by_panel'),conf))
            if not isinstance(devices,list):devices=devices.get('devices',[]) if isinstance(devices,dict) else []
            clean=[enrich_device_facts(d) for d in devices if isinstance(d,dict)]
            changes=[]
            for i,(old,new) in enumerate(zip(devices,clean)):
                stats['device_rows']+=1
                for field in ('brand','part_number'):
                    if new.get(field)!=old.get(field):
                        stats['backfillable_'+field]+=1
                        changes.append(dict(device_index=i,field=field,source=new['identity_review'][field].get('source_field')))
                stats['installation_reviews']+=1
            # Every saved quotation table, including per-panel drafts.
            tables={'quotation_rows':conf.get('quotation_rows') or []}
            tables.update({'panel:'+k:v for k,v in (conf.get('quotation_rows_by_panel') or {}).items() if isinstance(v,list)})
            design=conf.get('design_devices') or clean
            for name,rows in tables.items():
                if not rows:continue
                stats['quotation_tables']+=1
                enriched=enrich_quotation_facts(rows,design)
                for old,new in zip(rows,enriched):
                    if old.get('row_type') not in {'item','accessory'}:continue
                    stats['quotation_item_rows']+=1
                    for key in ('unit_price','line_total','quantity','price_row_id'):
                        assert old.get(key)==new.get(key), 'Commercial data changed'
                    for field in ('origin','sku'):
                        if old.get(field)!=new.get(field):stats['backfillable_quote_'+field]+=1
            if changes:revisions.append(dict(iteration_id=item['id'],changes=changes))
            if stats['iterations'] % 10 == 0:print(json.dumps({'audited_iterations':stats['iterations']}),flush=True)
    await engine.dispose()
    output=Path(__file__).resolve().parents[2]/'reports/dol-starter-20261116/quotation-audit.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(dict(summary=dict(stats),mode='read_only; enrichment applied on result reads',
        database_rows_modified=0,prices_modified=False,revisions=revisions),indent=2),encoding='utf8')
    print(json.dumps(dict(stats)))


if __name__=='__main__':
    try:asyncio.run(asyncio.wait_for(main(),timeout=300))
    except Exception as exc:
        print(json.dumps({'audit_status':'unavailable','error_type':type(exc).__name__}));sys.exit(1)

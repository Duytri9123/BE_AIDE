import asyncio,json,sys,time
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
from app.db.session import AsyncSessionLocal,engine
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.takeoff_scope import complete_accessories,compatible_accessory_candidates
async def main():
 out=Path('../outputs/live-system-takeoff-20261025');report=json.loads((out/'result.json').read_text(encoding='utf-8'))
 raw=next(d for d in report['result']['devices'] if d['category']=='MCCB' and d.get('accompanying_accessories'))
 parent=ExtractedDeviceSchema.model_validate(raw)
 old=parent.accompanying_accessories[0]['catalog_candidates']
 filtered=compatible_accessory_candidates(parent,old,'LS Electric')
 assert not filtered, 'Known wrong-frame and wrong-brand live suggestions must be rejected'
 print('PASS original incompatible live suggestions rejected',flush=True)
 start=time.monotonic()
 async with AsyncSessionLocal() as db:
  cs=await ConnectionPoolService.get_ordered_connections(db)
  await complete_accessories([parent],report['request'],cs,db,preferred_brand='LS Electric')
  await db.rollback()
 accessory=parent.accompanying_accessories[0]
 assert accessory['brand']=='LS Electric'
 assert set(accessory.get('catalog_candidates',{})).issubset({'LS Electric','LS'})
 (out/'accessory-retest.json').write_text(json.dumps({'status':'completed','seconds':round(time.monotonic()-start,1),'device':parent.model_dump(mode='json')},ensure_ascii=False,indent=2),encoding='utf-8')
 print('LIVE_ACCESSORY_RETEST',json.dumps({'seconds':round(time.monotonic()-start,1),'brand':accessory['brand'],'candidates':{b:len(rows) for b,rows in accessory['catalog_candidates'].items()},'missing_information':accessory.get('device_assessment',{}).get('missing_information')},ensure_ascii=False),flush=True)
 await engine.dispose()
asyncio.run(main())

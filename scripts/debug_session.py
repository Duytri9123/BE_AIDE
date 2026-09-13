import asyncio, json, sys
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id, iteration_number, ai_parsed_devices, confidence_scores FROM analysis_iterations WHERE session_id = 'f18f77021efc4146aee2f229976090fe'"))
        for r in res.fetchall():
            it_id, it_num, devs_json, scores_json = r
            devs = json.loads(devs_json) if devs_json else []
            scores = json.loads(scores_json) if scores_json else {}
            warnings = scores.get('warnings', [])
            print(f'Iteration {it_id} (num {it_num}): {len(devs)} devices, warnings: {warnings}')

if __name__ == '__main__':
    asyncio.run(main())

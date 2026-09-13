import asyncio, sys, os, traceback
from app.db.session import AsyncSessionLocal
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from sqlalchemy import select
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user import User
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with AsyncSessionLocal() as db:
        proj_res = await db.execute(select(Project).where(Project.id == 31))
        project = proj_res.scalar_one_or_none()
        file_res = await db.execute(select(ProjectFile).where(ProjectFile.id == 124))
        target_file = file_res.scalar_one_or_none()
        user_res = await db.execute(select(User).where(User.id == project.user_id))
        user = user_res.scalar_one_or_none()
        all_connections = await ConnectionPoolService.get_ordered_connections(db)
        active_ai = all_connections[0] if all_connections else None

        queue = asyncio.Queue()
        print('Active AI:', active_ai.name, active_ai.selected_model)

        async def log_watcher():
            while True:
                item = await queue.get()
                if item is None:
                    break
                print('QUEUE EVENT:', item.get('type') or item.get('stage'), '|', item.get('title'))

        watcher = asyncio.create_task(log_watcher())

        try:
            res = await AnalysisPipelineService.execute_analysis(
                project=project,
                project_files=[target_file],
                active_ai=active_ai,
                current_user=user,
                fallback_to_standard_template=False,
                user_prompt=None,
                db=db,
                all_connections=all_connections,
                generate_cad_and_quotation=False,
                progress_callback=queue.put,
                target_page=None
            )
            await queue.put(None)
            await watcher
            print('RESULT devices:', len(res.get('devices', [])))
            print('RESULT warnings:', res.get('warnings'))
        except Exception as e:
            await queue.put(None)
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main())

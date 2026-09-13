import asyncio, sys, os, traceback
sys.stdout.reconfigure(encoding="utf-8")

from app.db.session import AsyncSessionLocal
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
from sqlalchemy import select
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user import User

async def main():
    async with AsyncSessionLocal() as db:
        proj_res = await db.execute(select(Project).where(Project.id == 1))
        project = proj_res.scalar_one_or_none()
        file_res = await db.execute(select(ProjectFile).where(ProjectFile.id == 1))
        target_file = file_res.scalar_one_or_none()
        user_res = await db.execute(select(User).where(User.id == project.user_id))
        user = user_res.scalar_one_or_none()
        all_connections = await ConnectionPoolService.get_ordered_connections(db)
        active_ai = all_connections[0] if all_connections else None

        queue = asyncio.Queue()
        print("Project:", project.id, project.name)
        print("File:", target_file.id, target_file.filename, target_file.file_path, "Exists:", os.path.exists(target_file.file_path))
        print("Active AI:", active_ai.name, active_ai.selected_model)

        async def log_watcher():
            while True:
                item = await queue.get()
                if item is None:
                    break
                t = item.get("type") or item.get("stage")
                title = item.get("title")
                detail = item.get("detail")
                print(f"EVENT: [{t}] {title} - {detail}")

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

            devices = res.get("devices", [])
            print(f"\nSUCCESS! Total devices returned: {len(devices)}")
            for idx, d in enumerate(devices[:10]):
                print(f"  {idx+1}. [{d.category}] {d.name} | Spec: {d.spec} | In: {d.in_a}A | Brand: '{d.brand}' | Box: {d.box_2d} | Ev: {bool(d.evidence_image)}")

        except Exception as e:
            await queue.put(None)
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

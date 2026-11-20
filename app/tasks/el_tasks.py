import asyncio
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, name='app.tasks.el_tasks.run_el', max_retries=None)
def run_el(self, run_id):
    from app.services.ai.el_background import run
    from app.db.session import engine
    async def execute():
        try:
            return await run(run_id)
        finally:
            await engine.dispose()
    if asyncio.run(execute()) == 'BUSY':
        raise self.retry(countdown=120)

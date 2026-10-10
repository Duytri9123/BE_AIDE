import unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from app.services.job_queue import refresh_terminal_job


class TerminalRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_failure_releases_only_finished_job(self):
        info={'status':'PROGRESS','kind':'cad','project_id':'16'}
        with (patch('app.tasks.celery_app.celery_app.AsyncResult',return_value=SimpleNamespace(state='FAILURE')),
             patch('app.services.job_queue.publish') as publish,
             patch('app.services.job_queue.release') as release):
            result=await refresh_terminal_job('job-457',info)
        self.assertEqual(result['status'],'FAILURE')
        self.assertEqual(publish.call_args.args[0],'job-457')
        release.assert_called_once_with('job-457','16')

    async def test_running_job_does_not_release(self):
        info={'status':'PROGRESS','kind':'cad','project_id':'16'}
        with (patch('app.tasks.celery_app.celery_app.AsyncResult',return_value=SimpleNamespace(state='STARTED')),
             patch('app.services.job_queue.release') as release):
            self.assertEqual(await refresh_terminal_job('job-457',info),info)
        release.assert_not_called()

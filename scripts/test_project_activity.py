import unittest
import uuid
from unittest.mock import patch
from app.services import job_queue as jobs


class ProjectActivityTests(unittest.IsolatedAsyncioTestCase):
    async def test_active_paused_finished_and_unrequested_projects(self):
        prefix='aide:test:activity:'+uuid.uuid4().hex+':'
        with patch.object(jobs,'PREFIX',prefix):
            with jobs.sync_client() as c:
                for project_id,status in ((1,'PROGRESS'),(2,'PAUSED'),(3,'SUCCESS'),(4,'PENDING')):
                    c.set(prefix+f'project:{project_id}',str(project_id),ex=30)
                    c.hset(prefix+str(project_id),mapping={'project_id':str(project_id),'status':status,
                           'kind':'analysis','message':'Working','result':'must not load the result'})
                    c.expire(prefix+str(project_id),30)
            try:
                result=await jobs.project_activity([1,2,3,99])
                self.assertEqual(set(result),{1,2})
                self.assertFalse(result[1]['paused'])
                self.assertTrue(result[2]['paused'])
                self.assertNotIn('result',result[1])
                self.assertEqual(await jobs.project_activity([]),{})
            finally:
                with jobs.sync_client() as c:
                    keys=list(c.scan_iter(match=prefix+'*'))
                    if keys:c.delete(*keys)


if __name__=='__main__':unittest.main()

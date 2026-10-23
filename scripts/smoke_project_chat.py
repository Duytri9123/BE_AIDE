"""Exercise deployed project chat with an isolated temporary account/project."""
import asyncio
import json
import sys
import uuid
from datetime import timedelta
import httpx
from sqlalchemy import delete, select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.analysis_iteration import AnalysisIteration
from app.core.security import create_access_token

async def main():
    identifier = uuid.uuid4().hex
    async with AsyncSessionLocal() as db:
        user = User(email=f'chat-smoke-{identifier}@example.invalid', hashed_password='disabled',
                    name='Temporary chat smoke test', status='active', tokens=0)
        db.add(user)
        await db.flush()
        project = Project(user_id=user.id, name='Temporary chat smoke test')
        db.add(project)
        await db.commit()
        user_id, project_id = user.id, project.id
    history, devices, iteration = [], [], None
    base_url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.elquote.top/api/v1'
    results = []
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=120,
                headers={'Authorization':'Bearer '+create_access_token(user_id, timedelta(minutes=10))}) as client:
            async def chat(message):
                nonlocal devices, iteration
                history.append({'role':'user','content':message})
                payload = {'request_id':str(uuid.uuid4()),'project_id':project_id,'message':message,
                           'current_devices':devices,'context':{'iteration_id':iteration,'messages':history}}
                response = await client.post('/chat/',json=payload)
                response.raise_for_status()
                result = response.json()
                history.append({'role':'assistant','content':result['reply']})
                if result['action_type']=='update_devices':
                    devices, iteration = result['devices'], result['iteration_id']
                return result, payload
            result,_ = await chat('Xin chào')
            assert result['action_type']=='general_chat' and not devices
            results.append({'case':'greeting_without_synthetic_devices','passed':True})
            result,_ = await chat('Thêm một MCCB 100A vào danh sách thiết bị')
            assert len(devices)==1 and devices[0]['quantity']==1 and devices[0]['in_a']==100
            original_iteration = iteration
            results.append({'case':'add_one_device','passed':True})
            result,payload = await chat('thay bằng hãng ls giúp tôi nhé')
            assert devices[0]['brand'].upper()=='LS'
            repeated = await client.post('/chat/',json=payload)
            repeated.raise_for_status()
            assert repeated.json()['iteration_id']==iteration
            results.append({'case':'brand_change_and_idempotent_retry','passed':True})
            result,_ = await chat('Đổi số lượng thiết bị vừa thêm thành 2')
            assert len(devices)==1 and devices[0]['quantity']==2 and devices[0]['brand'].upper()=='LS'
            latest = await client.get(f'/analyze/project/{project_id}/latest')
            latest.raise_for_status()
            assert latest.json()['iteration_id']==iteration
            assert latest.json()['devices'][0]['quantity']==2
            results.append({'case':'followup_quantity_and_server_restore','passed':True})
            result,_ = await chat('Xóa MCCB vừa thêm khỏi danh sách')
            assert devices==[]
            latest = await client.get(f'/analyze/project/{project_id}/latest')
            latest.raise_for_status()
            assert latest.json()['devices']==[] and latest.json()['iteration_id']==iteration
            results.append({'case':'delete_last_device_and_restore_empty','passed':True})
            async with AsyncSessionLocal() as db:
                original = await db.get(AnalysisIteration, original_iteration)
                assert original.ai_parsed_devices[0]['quantity']==1
                results.append({'case':'original_revision_preserved','passed':True})
        print(json.dumps({'base_url':base_url,'tests':results},ensure_ascii=False),flush=True)
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Project).where(Project.id==project_id, Project.user_id==user_id))
            await db.execute(delete(User).where(User.id==user_id,User.email==f'chat-smoke-{identifier}@example.invalid'))
            await db.commit()
        print('Temporary test project/account removed.',flush=True)

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())

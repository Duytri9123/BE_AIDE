"""Owner-scoped, cooperative pause/resume for the existing worker job."""
from fastapi import APIRouter,Depends,HTTPException
import redis.asyncio as redis
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.services.job_queue import owned_job,PREFIX

router=APIRouter()

async def control(task_id,user,paused):
    info=await owned_job(task_id,user.id)
    if info['status'] in {'SUCCESS','FAILURE','CANCELLED'}:
        raise HTTPException(409,'Tác vụ đã kết thúc; không thể tạm dừng hoặc tiếp tục.')
    async with redis.from_url(settings.REDIS_URL,decode_responses=True) as client:
        await client.hset(PREFIX+task_id,'pause_requested','1' if paused else '0')
    return {'task_id':task_id,'status':'PAUSING' if paused else 'RESUMING',
            'message':'Sẽ tạm dừng sau bước AI đang chạy; giữ tiến trình để tiếp tục.' if paused else 'Đã yêu cầu tiếp tục tác vụ hiện tại.'}

@router.post('/task/{task_id}/pause')
async def pause(task_id:str,user=Depends(get_current_active_user)):
    return await control(task_id,user,True)

@router.post('/task/{task_id}/resume')
async def resume(task_id:str,user=Depends(get_current_active_user)):
    return await control(task_id,user,False)

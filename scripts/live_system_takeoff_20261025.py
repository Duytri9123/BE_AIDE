import asyncio,json,sys,traceback,time
from pathlib import Path
from sqlalchemy import select
sys.stdout.reconfigure(encoding='utf-8')
from app.db.session import AsyncSessionLocal,engine
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.user import User
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
OUT=Path('../outputs/live-system-takeoff-20261025');OUT.mkdir(parents=True,exist_ok=True)
PROMPT='Chỉ bóc tách trang 1 của hồ sơ này. Ưu tiên thiết bị hãng LS. Giữ đúng số cực, dòng định mức và khả năng cắt thể hiện trên bản vẽ. Với MCCB tổng, yêu cầu thêm cuộn cắt shunt trip cùng dòng tương thích; chưa có điện áp cuộn thì ghi cần xác minh, không mặc định 220V. Trình bày ngắn gọn dải/dòng thiết bị phù hợp, thông số của mã gợi ý và thông tin còn thiếu. Không tạo bản vẽ CAD hoặc báo giá trong lượt này.'
async def main():
 events=[];start=time.monotonic()
 async def progress(event):
  events.append(event)
  with (OUT/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False,default=str)+'\n')
  print(json.dumps({'elapsed':round(time.monotonic()-start,1),'stage':event.get('stage'),'title':event.get('title'),'detail':str(event.get('detail') or '')[:450]},ensure_ascii=False),flush=True)
 async with AsyncSessionLocal() as db:
  file=await db.get(ProjectFile,93);project=await db.get(Project,file.project_id);user=await db.get(User,project.user_id)
  connections=await ConnectionPoolService.get_ordered_connections(db)
  report={'project_id':project.id,'file_id':file.id,'filename':file.filename,'request':PROMPT,'provider':connections[0].provider,'model':connections[0].selected_model}
  try:
   result=await AnalysisPipelineService.execute_analysis(project=project,project_files=[file],active_ai=connections[0],current_user=user,db=db,all_connections=connections,user_prompt=PROMPT,target_page=1,generate_cad_and_quotation=False,progress_callback=progress,persist_partial_iterations=False)
   report['status']='completed';report['result']=result
  except Exception as e:
   report['status']='failed';report['error']=str(e);traceback.print_exc()
  finally:
   await db.rollback()
   report['elapsed_seconds']=round(time.monotonic()-start,1)
   (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=lambda obj:obj.model_dump(mode='json') if hasattr(obj,'model_dump') else str(obj)),encoding='utf-8')
   print('LIVE_TEST_RESULT',report['status'],report['elapsed_seconds'],flush=True)
 await engine.dispose()
asyncio.run(main())

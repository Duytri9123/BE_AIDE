import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException, UploadFile
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User, Plan, Payment, AiProvider, AiProviderModel, AiConnection
from app.services.upload_storage import save_upload
from app.services.request_metrics import RequestMetricsMiddleware, instrument_engine


class UploadStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_oversize_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'drawing.dxf'; target.write_bytes(b'original')
            upload=UploadFile(filename='drawing.dxf',file=io.BytesIO(b'x'*20),size=None)
            with self.assertRaises(HTTPException) as error:
                await save_upload(upload,Path(folder),10)
            self.assertEqual(error.exception.status_code,413)
            self.assertEqual(target.read_bytes(),b'original')
            self.assertEqual(list(Path(folder).glob('.upload-*')),[])

    async def test_upload_reads_bounded_chunks(self):
        with tempfile.TemporaryDirectory() as folder:
            upload=UploadFile(filename='drawing.dxf',file=io.BytesIO(b'x'*(2*1024*1024+7)))
            with patch.object(upload,'read',wraps=upload.read) as read:
                target,size=await save_upload(upload,Path(folder),3*1024*1024)
                self.assertEqual(size,target.stat().st_size)
                self.assertTrue(all(c.args==(1024*1024,) for c in read.call_args_list))

    async def test_invalid_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ('../a','..\\a','C:a'):
                with self.assertRaises(HTTPException):
                    await save_upload(UploadFile(filename=name,file=io.BytesIO(b'x')),Path(folder),10)


class RelationalApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
        self.factory=async_sessionmaker(self.engine,expire_on_commit=False)
        async with self.factory() as db:
            db.add(User(id=1,email='audit@example.invalid',hashed_password='unused'))
            db.add(Plan(id=1,name='Plan',price=10,token_amount=100,duration_months=1))
            await db.flush()
            for n in range(12): db.add(Payment(user_id=1,plan_id=1,amount=10,payment_method='test',status='completed'))
            for n in range(8):
                pid=f'p{n}'
                db.add(AiProvider(id=pid,name=pid,slug=pid,api_type='openai_compatible',is_active=True))
                await db.flush()
                db.add(AiProviderModel(provider_id=pid,model_key='model',label='Model',is_active=True))
                db.add(AiConnection(provider=pid,name='test',api_key='synthetic-not-real',status='active'))
            await db.commit()
        self.queries=[]
        event.listen(self.engine.sync_engine,'before_cursor_execute',lambda c,cur,sql,*args:self.queries.append(sql))

    async def asyncTearDown(self): await self.engine.dispose()

    async def test_payment_history_uses_one_join(self):
        from app.api.v1.endpoints.payments import get_my_payment_history
        async with self.factory() as db:
            items=await get_my_payment_history(current_user=SimpleNamespace(id=1),db=db)
            self.assertEqual(len(items),12); self.assertEqual(items[0].plan_name,'Plan')
            self.assertEqual(len(self.queries),1)

    async def test_agent_provider_list_has_two_queries_and_no_secrets(self):
        from app.api.v1.endpoints.cad_agent import providers
        async with self.factory() as db:
            result=await providers(db=db)
            self.assertEqual(len(result),8); self.assertEqual(len(self.queries),2)
            self.assertNotIn('synthetic-not-real',str(result))
            self.assertFalse(any('ai_connections.api_key' in q.split('FROM')[0] for q in self.queries))

    async def test_device_parameter_filters_apply_before_sql_page(self):
        from app.models import Brand, DeviceCategory, DeviceSeries, DeviceModel
        from app.api.v1.endpoints.devices import get_models
        async with self.factory() as db:
            db.add(Brand(id=1,name='Test')); db.add(DeviceCategory(id=1,name='MCB'))
            await db.flush()
            db.add(DeviceSeries(id=1,name='Series',brand_id=1,device_category_id=1))
            await db.flush()
            for n in range(6):
                db.add(DeviceModel(device_series_id=1,name='MCB',sku=f'T-{n}',
                       parameters={'p':1 if n<5 else 3,'in':32,'icu':10}))
            await db.commit()
        self.queries.clear()
        async with self.factory() as db:
            with patch('app.api.v1.endpoints.cad_library.manifest',return_value={'items':[]}):
                result=await get_models(poles=3,skip=0,limit=1,db=db)
            self.assertEqual([item.sku for item in result],['T-5'])
            self.assertIn('JSON_EXTRACT',self.queries[0])
            self.assertIn('LIMIT',self.queries[0])

    async def test_request_metrics_capture_sql_and_response_without_payload(self):
        instrument_engine(self.engine.sync_engine)
        async def app(scope,receive,send):
            async with self.factory() as db: await db.execute(select(User.id))
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':b'{}'})
        messages=[]
        async def send(message): messages.append(message)
        scope={'type':'http','method':'GET','path':'/api/v1/test','query_string':b'token=hidden'}
        await RequestMetricsMiddleware(app)(scope,None,send)
        timing=dict(messages[0]['headers'])[b'server-timing'].decode()
        self.assertIn('1 queries',timing); self.assertNotIn('hidden',timing)


if __name__=='__main__': unittest.main()


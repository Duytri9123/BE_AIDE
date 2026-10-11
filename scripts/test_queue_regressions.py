"""Quantity evidence and persisted worker results, with no real AI calls."""
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app.models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.base import Base
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.analysis_iteration import AnalysisIteration
from app.models.conversation_session import ConversationSession
from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.cad_label_integrity import reconcile_tagged_labels
from app.services.ai.response_parser import ResponseParserService
from app.tasks import worker_tasks
from app.services.ai.circuit_preflight import CircuitPreflightService


class Labels(unittest.TestCase):
    def devices(self):
        return ResponseParserService.parse_device_list(json.dumps({'devices':[
            {'category':'MCCB','name':'MCCB','spec':'3P 100A','in_a':100,'poles':3,'quantity':1},
            {'category':'MCB','name':'MCB','spec':'1P 16A','in_a':16,'poles':1,'quantity':1}]}))
    def texts(self):
        return [{'text':s} for s in ['QF1 MCCB 3P 100A 25kA QTY 1',
                                   'QF2 MCB 1P 16A 6kA QTY 1','QF3 MCB 1P 16A 6kA QTY 1']]
    def test_distinct_tags_preserve_three_physical_devices(self):
        result,_=reconcile_tagged_labels(self.devices(),self.texts())
        self.assertEqual({d.tag for d in result},{'QF1','QF2','QF3'})
        self.assertEqual(sum(d.quantity for d in result),3)
    def test_repeated_text_is_not_an_extra_device(self):
        result,_=reconcile_tagged_labels(self.devices(),self.texts()*2)
        self.assertEqual(sum(d.quantity for d in result),3)
    def test_regex_fallback_schema_keeps_unique_tags(self):
        original=[ExtractedDeviceSchema(category='MCCB',name='MCCB',spec='3P 100A',in_a=100,poles=3),
                  ExtractedDeviceSchema(category='MCB',name='MCB',spec='1P 16A',in_a=16,poles=1)]
        result,_=reconcile_tagged_labels(original,self.texts())
        self.assertEqual({d.tag for d in result},{'QF1','QF2','QF3'})
        self.assertEqual(sum(d.quantity for d in result),3)
    def test_multiple_panels_are_not_combined(self):
        original=self.devices()
        result,_=reconcile_tagged_labels(original,self.texts(),panel_count=2)
        self.assertEqual(sum(d.quantity for d in result),2)
    def test_conflicting_tag_is_not_used_as_quantity_evidence(self):
        texts=[{'text':'QF2 MCB 1P 16A 6kA QTY 1'}, {'text':'QF2 MCB 1P 32A 6kA QTY 1'}]
        result,_=reconcile_tagged_labels(self.devices(),texts)
        self.assertEqual(sum(d.quantity for d in result),2)


class Persistence(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        async with self.engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        async with self.sessions() as db:
            db.add(User(id=1,email='load-test@example.invalid',hashed_password='unused',tokens=100,status='active'))
            db.add(Project(id=1,name='isolated test',user_id=1))
            await db.flush()
            db.add(ProjectFile(id=1,project_id=1,filename='source.dxf',file_path='source.dxf',file_type='application/dxf',file_size=1,is_generated=False))
            await db.commit()
        self.result={'devices':[ExtractedDeviceSchema(category='MCB',name='MCB',spec='1P 16A',poles=1,in_a=16,quantity=2)],
                     'tokens_consumed':7,'warnings':[], 'enclosure_spec':{'sizing_status':'needs_review'}}
        self.patches=[patch.object(worker_tasks,'AsyncSessionLocal',self.sessions),
            patch.object(worker_tasks.ConnectionPoolService,'get_ordered_connections',AsyncMock(return_value=[SimpleNamespace(provider='test',selected_model='mock')])),
            patch.object(worker_tasks.AnalysisPipelineService,'execute_analysis',AsyncMock(return_value=self.result))]
        for p in self.patches:p.start()
    async def asyncTearDown(self):
        for p in reversed(self.patches):p.stop()
        await self.engine.dispose()
    async def test_two_jobs_save_json_uuid_counters_and_atomic_charge(self):
        first=await worker_tasks.run_analysis(1,1,{'file_id':1},lambda event:None)
        second=await worker_tasks.run_analysis(1,1,{'file_id':1},lambda event:None)
        self.assertTrue(all(call.kwargs.get('persist_partial_iterations') is False
                            for call in worker_tasks.AnalysisPipelineService.execute_analysis.call_args_list))
        json.dumps(first);json.dumps(second)
        async with self.sessions() as db:
            iterations=(await db.execute(select(AnalysisIteration).order_by(AnalysisIteration.id))).scalars().all()
            session=(await db.execute(select(ConversationSession))).scalar_one()
            user=await db.get(User,1)
            self.assertEqual([i.iteration_number for i in iterations],[1,2])
            self.assertEqual(iterations[0].ai_parsed_devices[0]['quantity'],2)
            self.assertEqual(session.total_tokens_used,14)
            self.assertEqual(session.total_iterations,2)
            self.assertEqual(user.tokens,86)
            self.assertEqual(first['session_id'],second['session_id'])
    async def test_insufficient_tokens_roll_back_results(self):
        self.result['tokens_consumed']=101
        with self.assertRaises(ValueError):
            await worker_tasks.run_analysis(1,1,{},lambda event:None)
        async with self.sessions() as db:
            self.assertEqual((await db.get(User,1)).tokens,100)
            self.assertEqual((await db.execute(select(AnalysisIteration))).scalars().all(),[])
    async def test_missing_source_file_rejected_before_ai(self):
        with self.assertRaises(ValueError):
            await worker_tasks.run_analysis(1,1,{'file_id':999},lambda event:None)
        worker_tasks.AnalysisPipelineService.execute_analysis.assert_not_awaited()


class Preflight(unittest.IsolatedAsyncioTestCase):
    async def test_malformed_output_retried_once_without_forcing_sld(self):
        mock=AsyncMock(side_effect=[('not JSON',None),(json.dumps({'circuit_summary':'Only technical metadata','has_sld':False}),None)])
        with patch.object(CircuitPreflightService,'_visual_pages',return_value=[]),\
             patch.object(worker_tasks.ConnectionPoolService,'call_with_fallback',mock):
            result=await CircuitPreflightService.assess([], [{'filename':'a.dxf','text':'MCB'}],object(),[object()])
        self.assertEqual(mock.await_count,2)
        self.assertFalse(result.get('has_sld'))
        self.assertEqual(result['status'],'unavailable')


if __name__=='__main__':
    unittest.main()

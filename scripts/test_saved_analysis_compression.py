import unittest
import httpx
from fastapi import FastAPI
from starlette.responses import StreamingResponse
from app.services.saved_analysis_compression import SavedAnalysisCompression


class SavedAnalysisCompressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_saved_detail_compressed_and_events_untouched(self):
        app=FastAPI()
        app.add_middleware(SavedAnalysisCompression,prefix='/api/v1/analyze/iteration/')
        @app.get('/api/v1/analyze/iteration/1')
        async def detail():return {'image':'A'*100000}
        @app.get('/api/v1/analyze/task/1/events')
        async def stream():
            async def events():yield 'data: '+('A'*10000)+'\n\n'
            return StreamingResponse(events(),media_type='text/event-stream')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            saved=await client.get('/api/v1/analyze/iteration/1',headers={'Accept-Encoding':'gzip'})
            self.assertEqual(saved.headers.get('content-encoding'),'gzip')
            self.assertEqual(saved.json()['image'],'A'*100000)
            self.assertLess(int(saved.headers['content-length']),2000)
            events=await client.get('/api/v1/analyze/task/1/events',headers={'Accept-Encoding':'gzip'})
            self.assertNotIn('content-encoding',events.headers)


if __name__=='__main__':unittest.main()

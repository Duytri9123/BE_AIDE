"""Run the new CAD router against real auth/DB alongside the existing backend."""
from fastapi import FastAPI
from app.api.v1.endpoints.cad_agent import router

app = FastAPI()
app.include_router(router, prefix='/api/v1/cad-agent')

@app.get('/health')
async def health():
    return {'status': 'ok', 'scope': 'cad-agent integration audit'}

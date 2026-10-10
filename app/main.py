import contextlib
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles

from app.admin.setup import create_admin
from app.api.v1.api_router import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.session import AsyncSessionLocal
from app.db.seed_prompt_templates import seed_default_prompt_templates
from app.db.seed_plans import seed_default_plans
from app.services.activity_logger import sync_initial_activities_and_notifications

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_default_prompt_templates(db)
        await seed_default_plans(db)
        await sync_initial_activities_and_notifications(db)
    yield
    await engine.dispose()

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan,
              docs_url='/docs' if settings.DEBUG and settings.EXPOSE_API_DOCS else None,
              redoc_url='/redoc' if settings.DEBUG and settings.EXPOSE_API_DOCS else None,
              openapi_url='/openapi.json' if settings.DEBUG and settings.EXPOSE_API_DOCS else None)

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=['127.0.0.1', '::1'])

# Filter out wildcard '*' from explicit origins when allow_credentials=True to satisfy Starlette CORS constraints
cors_origins = [o.strip() for o in settings.CORS_ORIGINS if o.strip() != "*"] if isinstance(settings.CORS_ORIGINS, list) else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ['http://localhost:5173', 'http://127.0.0.1:5173', 'https://elquote.top', 'https://www.elquote.top'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

import os
_admin_static = os.path.join(os.path.dirname(__file__), "admin", "static")
if os.path.isdir(_admin_static):
    app.mount("/admin/static", StaticFiles(directory=_admin_static), name="admin-static")

admin = create_admin(app, engine)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.middleware('http')
async def protect_private_library(request, call_next):
    from fastapi.responses import JSONResponse
    path = request.url.path.lower()
    if path.startswith(('/data/', '/@fs/', '/src/', '/.git', '/.env')):
        return JSONResponse({'detail': 'Not found'}, status_code=404)
    response = await call_next(request)
    if any(path.startswith(settings.API_V1_STR + '/' + name) for name in
           ('library-access', 'equipment-library', 'cad-library', 'curated-library',
            'cabinet-templates', 'device-library', 'catalog-prices')):
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Vary'] = 'Authorization, Cookie, Origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response
# app.include_router(websocket_router, prefix="/ws")

@app.get("/")
async def root():
    return RedirectResponse(url="/admin", status_code=302)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

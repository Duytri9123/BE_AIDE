import contextlib
from fastapi import FastAPI
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

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
# app.include_router(websocket_router, prefix="/ws")

@app.get("/")
async def root():
    return {
        "message": f"{settings.PROJECT_NAME} Server",
        "version": settings.VERSION,
        "docs": "/docs",
        "admin": "/admin",
        "api": settings.API_V1_STR
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

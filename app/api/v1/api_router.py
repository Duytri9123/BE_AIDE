from fastapi import APIRouter
from .endpoints import analyze, analyze_multi_agent, bom, export, chat, user_library, auth, users, projects, devices, providers, admin_helpers, plans, payments

api_router = APIRouter()
from .endpoints import cad_library
api_router.include_router(cad_library.router, prefix="/cad-library", tags=["CAD Library"])
from .endpoints import cabinet_templates
api_router.include_router(cabinet_templates.router, prefix="/cabinet-templates", tags=["Cabinet Templates"])
from .endpoints import catalog_prices
api_router.include_router(catalog_prices.router, prefix="/catalog-prices", tags=["Catalog & Custom Prices"])
from .endpoints import ads
api_router.include_router(ads.router, prefix="/ads", tags=["Ads"])

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(plans.router, prefix="/plans", tags=["Plans"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(devices.router, prefix="/device-library", tags=["Devices"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
api_router.include_router(analyze_multi_agent.router, prefix="/analyze", tags=["Multi-Agent Analyze"])
api_router.include_router(bom.router, prefix="/bom", tags=["BOM"])
api_router.include_router(export.router, prefix="/export", tags=["Export"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers"])
api_router.include_router(user_library.router, prefix="/user-library", tags=["User Library"])
api_router.include_router(admin_helpers.router, tags=["Admin Helpers"])

from fastapi import APIRouter

from app.modules.assets.router import router as assets_router
from app.modules.drafts.router import router as drafts_router
from app.modules.evidence.router import router as evidence_router
from app.modules.projects.router import router as projects_router
from app.modules.systems.router import router as systems_router

api_router = APIRouter()

api_router.include_router(projects_router)
api_router.include_router(systems_router)
api_router.include_router(assets_router)
api_router.include_router(drafts_router)
api_router.include_router(evidence_router)

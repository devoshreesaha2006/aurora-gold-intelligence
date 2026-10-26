from fastapi import APIRouter
from backend.app.api.health import router as health_router
from backend.app.api.market import router as market_router
from backend.app.api.contracts import router as contracts_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.backtests import router as backtests_router
from backend.app.api.research import router as research_router

api_router = APIRouter(prefix="/api")

api_router.include_router(health_router)
api_router.include_router(market_router)
api_router.include_router(contracts_router)
api_router.include_router(ingestion_router)
api_router.include_router(analytics_router)
api_router.include_router(backtests_router)
api_router.include_router(research_router)

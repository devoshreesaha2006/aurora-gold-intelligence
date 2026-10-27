from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.database import get_db
from backend.app.config import settings
from backend.app.schemas.common import StandardResponse

router = APIRouter(tags=["System Health"])


@router.get("/health", response_model=StandardResponse[dict])
def get_health(db: Session = Depends(get_db)):
    """
    Lightweight liveness/readiness probe.
    Do not call market-status analytics here: health checks must remain fast
    even when historical observations are large or analytics queries are slow.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"disconnected: {type(exc).__name__}"

    return StandardResponse(
        success=(db_status == "connected"),
        message="AURORA backend operational" if db_status == "connected" else "AURORA database unavailable",
        data={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.aurora_env,
            "database": db_status,
            "data_mode": settings.data_mode,
            "data_mode_is_configured": True,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }
    )

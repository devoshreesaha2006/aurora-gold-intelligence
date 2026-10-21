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
    Health check endpoint.
    Verifies service liveness and database connectivity.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return StandardResponse(
        success=(db_status == "connected"),
        message="AURORA backend operational",
        data={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.aurora_env,
            "database": db_status,
            "data_mode": settings.data_mode,
            "server_time": datetime.now(timezone.utc).isoformat()
        }
    )

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.backtest import BacktestRequest, BacktestResponse
from backend.app.schemas.common import StandardResponse
from backend.app.services.backtest_service import BacktestService


router = APIRouter(prefix="/backtests", tags=["Historical Backtesting"])


@router.post("/run", response_model=StandardResponse[BacktestResponse])
def run_historical_backtest(request: BacktestRequest, db: Session = Depends(get_db)):
    """Run a close-to-close mean-reversion backtest on eligible imported observations."""
    result = BacktestService(db).run(request)
    return StandardResponse(success=True, message=result.message, data=result)

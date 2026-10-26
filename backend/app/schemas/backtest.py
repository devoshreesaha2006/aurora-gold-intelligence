from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


SUPPORTED_PAIRS = {
    "GOLDM-GOLDTEN", "GOLDM-GOLDGUINEA", "GOLDM-GOLDPETAL",
    "GOLDTEN-GOLDGUINEA", "GOLDTEN-GOLDPETAL", "GOLDGUINEA-GOLDPETAL",
}


class BacktestRequest(BaseModel):
    pair: str = "GOLDM-GOLDPETAL"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    capital: float = Field(default=100000, gt=0, le=1_000_000_000)
    units: int = Field(default=1, ge=1, le=10000, description="10g normalized spread units")
    lookback: int = Field(default=30, ge=5, le=365)
    entry_z: float = Field(default=2.0, ge=0.5, le=5)
    exit_z: float = Field(default=0.5, ge=0, le=2)
    transaction_cost_per_10g: float = Field(default=10.31, ge=0, le=100000)
    slippage_per_10g: float = Field(default=15, ge=0, le=100000)
    min_volume: int = Field(default=0, ge=0, le=100_000_000)
    expiry_buffer_days: int = Field(default=3, ge=0, le=60)

    @model_validator(mode="after")
    def validate_config(self):
        self.pair = self.pair.strip().upper().replace("_", "-").replace("/", "-")
        if self.pair not in SUPPORTED_PAIRS:
            raise ValueError("Unsupported contract pair.")
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("Start date must be on or before end date.")
        if self.exit_z >= self.entry_z:
            raise ValueError("Exit Z-score must be lower than entry Z-score.")
        return self


class BacktestMetricSet(BaseModel):
    total_return_pct: Optional[float] = None
    total_pnl: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate_pct: Optional[float] = None
    total_trades: int = 0
    profit_factor: Optional[float] = None
    gross_pnl: Optional[float] = None
    total_costs: Optional[float] = None
    # Capital-scaled passive normalized-price benchmarks; not exposure-matched alpha.
    benchmark_leg_a_return_pct: Optional[float] = None
    benchmark_leg_b_return_pct: Optional[float] = None
    benchmark_leg_a_pnl: Optional[float] = None
    benchmark_leg_b_pnl: Optional[float] = None
    excess_return_vs_leg_a_pct: Optional[float] = None
    excess_return_vs_leg_b_pct: Optional[float] = None


class EquityPoint(BaseModel):
    trade_date: date
    equity: float
    drawdown_pct: float


class SpreadPoint(BaseModel):
    trade_date: date
    spread: float
    execution: Optional[str] = None


class BacktestTrade(BaseModel):
    entry_date: date
    exit_date: date
    pair: str
    direction: str
    entry_spread: float
    exit_spread: float
    units: int
    gross_pnl: float
    costs: float
    net_pnl: float
    exit_reason: str


class BacktestResponse(BaseModel):
    status: str
    message: str
    pair: str
    data_source: Optional[str] = None
    first_date: Optional[date] = None
    last_date: Optional[date] = None
    observations: int = 0
    metrics: BacktestMetricSet
    equity_curve: List[EquityPoint] = []
    spread_series: List[SpreadPoint] = []
    trades: List[BacktestTrade] = []
    assumptions: List[str] = []

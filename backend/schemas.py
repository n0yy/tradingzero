from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

class HealthResponse(BaseModel):
    status: str

class RunStatusResponse(BaseModel):
    state: str
    run_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorDetail

class EventItem(BaseModel):
    type: str
    message: str
    created_at: str

class EventListResponse(BaseModel):
    events: list[EventItem]

class RunErrorItem(BaseModel):
    code: str
    message: str
    details: str | None = None
    created_at: str

class RunErrorListResponse(BaseModel):
    errors: list[RunErrorItem]

class RunHistoryItem(BaseModel):
    run_id: str
    state: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

class RunHistoryResponse(BaseModel):
    runs: list[RunHistoryItem]

class DataConfig(BaseModel):
    exchange: str = Field(min_length=1)
    symbol: str = Field(min_length=3)
    timeframe: str = Field(min_length=1)
    window_size: int = Field(ge=10, le=500)

class EnvConfig(BaseModel):
    initial_balance: float = Field(gt=0)
    transaction_cost: float = Field(ge=0, le=0.1)
    episode_length: int = Field(ge=10, le=50000)

class AgentConfig(BaseModel):
    learning_rate: float = Field(gt=0, le=1)
    n_steps: int = Field(ge=16, le=65536)
    batch_size: int = Field(ge=8, le=4096)
    clip_range: float = Field(gt=0, le=1)
    total_episodes: int = Field(ge=1, le=100000)
    promote_threshold: float = Field(ge=0, le=10)

class SelfPlayConfig(BaseModel):
    checkpoint_interval: int = Field(ge=1, le=100000)
    checkpoint_dir: str = Field(min_length=1)

class SafeConfigPayload(BaseModel):
    model_config = ConfigDict(extra='forbid')

    data: DataConfig
    env: EnvConfig
    agent: AgentConfig
    self_play: SelfPlayConfig

class ActiveConfigResponse(BaseModel):
    version: str | None = None
    created_at: str | None = None
    config: SafeConfigPayload | None = None


class BattleTrade(BaseModel):
    action: str
    timestamp: str
    execution_price: float
    size_percent: float
    position_before: float
    position_after: float
    notional_usd: float
    balance_before: float
    balance_after: float
    fee: float
    realized_pnl: float
    unrealized_pnl_after: float


class BattleResultResponse(BaseModel):
    checkpoint: str
    symbol: str
    timeframe: str
    initial_balance: float
    final_balance: float
    pnl: float
    pnl_pct: float
    total_steps: int
    total_trades: int
    trade_win_rate: float
    winning_trades: int
    losing_trades: int
    flat_trades: int
    transaction_distribution: dict[str, int]
    price_series: list[float]
    equity_curve: list[float]
    executed_trades: list[BattleTrade]

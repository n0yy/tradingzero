from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel


class LastAction(BaseModel):
    action: Literal['BUY', 'SELL', 'HOLD']
    timestamp: str
    execution_price: float
    size_percent: float
    position_before: float
    position_after: float
    notional_usd: float
    balance_before: float
    balance_after: float
    fee: float
    unrealized_pnl_after: float


class TrainingUpdateData(BaseModel):
    generation: int
    current_sharpe: float
    best_sharpe: float
    balance: float
    pnl: float
    win_rate: float
    progress: float
    action_distribution: dict[str, int]
    cumulative_buys: int
    cumulative_sells: int
    last_action: LastAction


class TrainingUpdateEvent(BaseModel):
    type: Literal['training_update']
    data: TrainingUpdateData


class StepBatchData(BaseModel):
    step: int
    generation: int
    price: float
    last_action: Literal['BUY', 'SELL', 'HOLD']
    position: float
    balance: float
    pnl: float
    rolling_reward: float
    steps_per_second: float
    equity_curve: list[float]
    timestamp: str


class StepBatchEvent(BaseModel):
    type: Literal['step_batch']
    data: StepBatchData


def _map_last_action(payload: dict) -> LastAction:
    actions = payload.get('action_series') or []
    prices = payload.get('price_series') or []
    action_int = int(actions[-1]) if actions else 0
    action = 'HOLD' if action_int == 0 else 'BUY' if action_int == 1 else 'SELL'
    execution_price = float(prices[-1]) if prices else float(payload.get('final_balance', 0.0))
    balance_after = float(payload.get('final_balance', 0.0))
    balance_before = float(payload.get('initial_balance', balance_after))

    return LastAction(
        action=action,
        timestamp=datetime.now(UTC).isoformat(),
        execution_price=execution_price,
        size_percent=0.0,
        position_before=0.0,
        position_after=0.0,
        notional_usd=0.0,
        balance_before=balance_before,
        balance_after=balance_after,
        fee=0.0,
        unrealized_pnl_after=float(payload.get('pnl', 0.0)),
    )


def map_training_payload(payload: dict) -> dict:
    total_generations = max(int(payload.get('total_generations', 1)), 1)
    generation = int(payload.get('generation', 0))
    event = TrainingUpdateEvent(
        type='training_update',
        data=TrainingUpdateData(
            generation=generation,
            current_sharpe=float(payload.get('current_sharpe', 0.0)),
            best_sharpe=float(payload.get('best_sharpe', 0.0)),
            balance=float(payload.get('final_balance', 0.0)),
            pnl=float(payload.get('pnl', 0.0)),
            win_rate=float(payload.get('win_rate', 0.0)),
            progress=min(max(generation / total_generations, 0.0), 1.0),
            action_distribution={
                'buy': int((payload.get('action_counts') or {}).get('buy', 0)),
                'hold': int((payload.get('action_counts') or {}).get('hold', 0)),
                'sell': int((payload.get('action_counts') or {}).get('sell', 0)),
            },
            cumulative_buys=int(payload.get('cumulative_buys', 0)),
            cumulative_sells=int(payload.get('cumulative_sells', 0)),
            last_action=_map_last_action(payload),
        ),
    )
    return event.model_dump()


def _action_label(value: int) -> Literal['BUY', 'SELL', 'HOLD']:
    if value == 1:
        return 'BUY'
    if value == 2:
        return 'SELL'
    return 'HOLD'


def map_step_batch_payload(payload: dict) -> dict:
    event = StepBatchEvent(
        type='step_batch',
        data=StepBatchData(
            step=int(payload.get('step', 0)),
            generation=int(payload.get('generation', 0)),
            price=float(payload.get('price', 0.0)),
            last_action=_action_label(int(payload.get('last_action', 0))),
            position=float(payload.get('position', 0.0)),
            balance=float(payload.get('balance', 0.0)),
            pnl=float(payload.get('pnl', 0.0)),
            rolling_reward=float(payload.get('rolling_reward', 0.0)),
            steps_per_second=float(payload.get('steps_per_second', 0.0)),
            equity_curve=[float(x) for x in (payload.get('equity_curve') or [])],
            timestamp=payload.get('timestamp') or datetime.now(UTC).isoformat(),
        ),
    )
    return event.model_dump()

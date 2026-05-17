from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel


class ExecutedTrade(BaseModel):
    action: Literal['BUY', 'SELL']
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
    hold_duration: int = 0


class PromotionGateCheck(BaseModel):
    name: str
    passed: bool
    actual: float | int | None = None
    target: float | int | None = None
    message: str


class TrainingUpdateData(BaseModel):
    generation: int
    training_sharpe: float
    evaluation_sharpe: float
    best_evaluation_sharpe: float
    promoted: bool
    evaluation_executed_trade_count: int
    evaluation_sell_realized_exit_count: int
    promotion_gate_reasons: list[str]
    promotion_gate_checks: list[PromotionGateCheck]
    balance: float
    pnl: float
    trade_win_rate: float
    progress: float
    transaction_distribution: dict[str, int]
    cumulative_buys: int
    cumulative_sells: int
    winning_trades: int
    losing_trades: int
    flat_trades: int
    last_transaction: ExecutedTrade | None


class TrainingUpdateEvent(BaseModel):
    type: Literal['training_update']
    data: TrainingUpdateData


class StepBatchData(BaseModel):
    step: int
    generation: int
    price: float
    requested_direction: Literal['BUY', 'SELL', 'HOLD']
    requested_size_percent: float
    transaction_outcome: Literal['BUY', 'SELL', 'NO_TRANSACTION']
    is_transaction: bool
    position_before: float
    position_after: float
    executed_delta: float
    position: float
    balance: float
    pnl: float
    rolling_reward: float
    steps_per_second: float
    equity_curve: list[float]
    cost: float
    cumulative_buys: int
    cumulative_sells: int
    transaction_distribution: dict[str, int]
    trade_win_rate: float
    winning_trades: int
    losing_trades: int
    flat_trades: int
    executed_trade: ExecutedTrade | None
    timestamp: str
    phase: Literal['training', 'evaluation'] = 'training'


class StepBatchEvent(BaseModel):
    type: Literal['step_batch']
    data: StepBatchData


def _transaction_distribution(payload: dict) -> dict[str, int]:
    counts = payload.get('transaction_distribution') or payload.get('action_counts') or {}
    return {
        'buy': int(counts.get('buy', 0)),
        'sell': int(counts.get('sell', 0)),
        'no_transaction': int(counts.get('no_transaction', counts.get('hold', 0))),
    }


def _executed_trade(payload: dict | None) -> ExecutedTrade | None:
    if not payload:
        return None
    action = payload.get('action')
    if action not in {'BUY', 'SELL'}:
        return None
    return ExecutedTrade(
        action=action,
        timestamp=payload.get('timestamp') or datetime.now(UTC).isoformat(),
        execution_price=float(payload.get('execution_price', 0.0)),
        size_percent=float(payload.get('size_percent', 0.0)),
        position_before=float(payload.get('position_before', 0.0)),
        position_after=float(payload.get('position_after', 0.0)),
        notional_usd=float(payload.get('notional_usd', 0.0)),
        balance_before=float(payload.get('balance_before', 0.0)),
        balance_after=float(payload.get('balance_after', 0.0)),
        fee=float(payload.get('fee', 0.0)),
        realized_pnl=float(payload.get('realized_pnl', 0.0)),
        unrealized_pnl_after=float(payload.get('unrealized_pnl_after', 0.0)),
        hold_duration=int(payload.get('hold_duration', 0)),
    )


def map_training_payload(payload: dict) -> dict:
    total_generations = max(int(payload.get('total_generations', 1)), 1)
    generation = int(payload.get('generation', 0))
    event = TrainingUpdateEvent(
        type='training_update',
        data=TrainingUpdateData(
            generation=generation,
            training_sharpe=float(payload.get('training_sharpe', payload.get('current_sharpe', 0.0))),
            evaluation_sharpe=float(payload.get('evaluation_sharpe', payload.get('current_sharpe', 0.0))),
            best_evaluation_sharpe=float(
                payload.get('best_evaluation_sharpe', payload.get('best_sharpe', 0.0))
            ),
            promoted=bool(payload.get('promoted', False)),
            evaluation_executed_trade_count=int(payload.get('evaluation_executed_trade_count', 0)),
            evaluation_sell_realized_exit_count=int(payload.get('evaluation_sell_realized_exit_count', 0)),
            promotion_gate_reasons=[str(item) for item in (payload.get('promotion_gate_reasons') or [])],
            promotion_gate_checks=[
                PromotionGateCheck(
                    name=str(item.get('name', 'unknown')),
                    passed=bool(item.get('passed', False)),
                    actual=item.get('actual'),
                    target=item.get('target'),
                    message=str(item.get('message', '')),
                )
                for item in (payload.get('promotion_gate_checks') or [])
            ],
            balance=float(payload.get('final_balance', 0.0)),
            pnl=float(payload.get('pnl', 0.0)),
            trade_win_rate=float(payload.get('trade_win_rate', payload.get('win_rate', 0.0))),
            progress=min(max(generation / total_generations, 0.0), 1.0),
            transaction_distribution=_transaction_distribution(payload),
            cumulative_buys=int(payload.get('cumulative_buys', 0)),
            cumulative_sells=int(payload.get('cumulative_sells', 0)),
            winning_trades=int(payload.get('winning_trades', 0)),
            losing_trades=int(payload.get('losing_trades', 0)),
            flat_trades=int(payload.get('flat_trades', 0)),
            last_transaction=_executed_trade(payload.get('last_transaction')),
        ),
    )
    return event.model_dump()


def _requested_direction(payload: dict) -> Literal['BUY', 'SELL', 'HOLD']:
    value = payload.get('requested_direction')
    if value in {'BUY', 'SELL', 'HOLD'}:
        return value
    legacy = int(payload.get('last_action', 0))
    if legacy == 1:
        return 'BUY'
    if legacy == 2:
        return 'SELL'
    return 'HOLD'


def _transaction_outcome(payload: dict) -> Literal['BUY', 'SELL', 'NO_TRANSACTION']:
    value = payload.get('transaction_outcome')
    if value in {'BUY', 'SELL', 'NO_TRANSACTION'}:
        return value
    executed_delta = float(payload.get('executed_delta', 0.0))
    if executed_delta > 0:
        return 'BUY'
    if executed_delta < 0:
        return 'SELL'
    return 'NO_TRANSACTION'


def map_step_batch_payload(payload: dict) -> dict:
    transaction_outcome = _transaction_outcome(payload)
    event = StepBatchEvent(
        type='step_batch',
        data=StepBatchData(
            step=int(payload.get('step', 0)),
            generation=int(payload.get('generation', 0)),
            price=float(payload.get('price', 0.0)),
            requested_direction=_requested_direction(payload),
            requested_size_percent=float(payload.get('requested_size_percent', 0.0)),
            transaction_outcome=transaction_outcome,
            is_transaction=bool(payload.get('is_transaction', transaction_outcome != 'NO_TRANSACTION')),
            position_before=float(payload.get('position_before', 0.0)),
            position_after=float(payload.get('position_after', payload.get('position', 0.0))),
            executed_delta=float(payload.get('executed_delta', 0.0)),
            position=float(payload.get('position_after', payload.get('position', 0.0))),
            balance=float(payload.get('balance', 0.0)),
            pnl=float(payload.get('pnl', 0.0)),
            rolling_reward=float(payload.get('rolling_reward', 0.0)),
            steps_per_second=float(payload.get('steps_per_second', 0.0)),
            equity_curve=[float(x) for x in (payload.get('equity_curve') or [])],
            cost=float(payload.get('cost', 0.0)),
            cumulative_buys=int(payload.get('cumulative_buys', 0)),
            cumulative_sells=int(payload.get('cumulative_sells', 0)),
            transaction_distribution=_transaction_distribution(payload),
            trade_win_rate=float(payload.get('trade_win_rate', 0.0)),
            winning_trades=int(payload.get('winning_trades', 0)),
            losing_trades=int(payload.get('losing_trades', 0)),
            flat_trades=int(payload.get('flat_trades', 0)),
            executed_trade=_executed_trade(payload.get('executed_trade')),
            timestamp=payload.get('timestamp') or datetime.now(UTC).isoformat(),
            phase=payload.get('phase', 'training'),
        ),
    )
    return event.model_dump()

from __future__ import annotations

import math
import random
from threading import Event, Thread
from typing import Callable, Protocol
from datetime import UTC, datetime

from backend.training_runtime import build_trainer_runtime


class RunnerAdapter(Protocol):
    def run(self) -> None: ...
    def stop(self) -> None: ...


class InMemoryRunnerAdapter:
    def __init__(
        self,
        on_update: Callable[[dict], None] | None = None,
        tick_interval: float = 1.5,
        step_interval: float = 0.1,
        total_generations: int = 200,
        seed: int = 7,
    ) -> None:
        self._stop_event = Event()
        self._on_update = on_update
        self._tick_interval = tick_interval
        self._step_interval = step_interval
        self._total_generations = total_generations
        self._rng = random.Random(seed)

    def run(self) -> None:
        if self._on_update is None:
            self._stop_event.wait()
            return

        def empty_transaction_distribution() -> dict[str, int]:
            return {'buy': 0, 'sell': 0, 'no_transaction': 0}

        balance = 10_000.0
        best_sharpe = 0.0
        cumulative_buys = 0
        cumulative_sells = 0
        winning_trades = 0
        losing_trades = 0
        flat_trades = 0
        price = 30_000.0
        position = 0.0
        equity_curve: list[float] = [balance]
        steps_per_generation = max(int(self._tick_interval / self._step_interval), 1)
        global_step = 0

        for generation in range(1, self._total_generations + 1):
            transaction_distribution = empty_transaction_distribution()
            outcomes: list[int] = []
            prices: list[float] = []
            gen_start_balance = balance
            last_transaction: dict | None = None

            for _ in range(steps_per_generation):
                if self._stop_event.wait(timeout=self._step_interval):
                    return
                global_step += 1
                price *= 1 + self._rng.uniform(-0.0015, 0.0015)
                action = self._rng.choices([0, 1, 2], weights=[6, 2, 2])[0]
                requested_direction = 'HOLD' if action == 0 else 'BUY' if action == 1 else 'SELL'
                requested_size_percent = 0.1
                position_before = position
                if action == 1:
                    position = min(position + 0.1, 1.0)
                elif action == 2:
                    position = max(position - 0.1, 0.0)
                executed_delta = position - position_before
                transaction_outcome = 'BUY' if executed_delta > 0 else 'SELL' if executed_delta < 0 else 'NO_TRANSACTION'
                if transaction_outcome == 'BUY':
                    cumulative_buys += 1
                    transaction_distribution['buy'] += 1
                elif transaction_outcome == 'SELL':
                    cumulative_sells += 1
                    transaction_distribution['sell'] += 1
                else:
                    transaction_distribution['no_transaction'] += 1
                outcomes.append(1 if transaction_outcome == 'BUY' else 2 if transaction_outcome == 'SELL' else 0)
                prices.append(price)
                step_pnl = self._rng.uniform(-3.0, 4.0) + position * (price - prices[0]) * 0.0001
                balance_before = balance
                balance += step_pnl
                equity_curve.append(balance)
                if len(equity_curve) > 200:
                    equity_curve = equity_curve[-200:]
                timestamp = datetime.now(UTC).isoformat()
                executed_trade = None
                if transaction_outcome != 'NO_TRANSACTION':
                    realized_pnl = step_pnl if transaction_outcome == 'SELL' else 0.0
                    executed_trade = {
                        'action': transaction_outcome,
                        'timestamp': timestamp,
                        'execution_price': price,
                        'size_percent': abs(executed_delta),
                        'position_before': position_before,
                        'position_after': position,
                        'notional_usd': balance_before * abs(executed_delta),
                        'balance_before': balance_before,
                        'balance_after': balance,
                        'fee': balance_before * 0.001 * abs(executed_delta),
                        'realized_pnl': realized_pnl,
                        'unrealized_pnl_after': step_pnl,
                    }
                    last_transaction = executed_trade
                    if transaction_outcome == 'SELL':
                        if realized_pnl > 0:
                            winning_trades += 1
                        elif realized_pnl < 0:
                            losing_trades += 1
                        else:
                            flat_trades += 1

                self._on_update({
                    'kind': 'step_batch',
                    'step': global_step,
                    'generation': generation,
                    'price': price,
                    'requested_direction': requested_direction,
                    'requested_size_percent': requested_size_percent,
                    'transaction_outcome': transaction_outcome,
                    'is_transaction': transaction_outcome != 'NO_TRANSACTION',
                    'position_before': position_before,
                    'position_after': position,
                    'executed_delta': executed_delta,
                    'position': position,
                    'balance': balance,
                    'pnl': balance - 10_000.0,
                    'rolling_reward': step_pnl,
                    'steps_per_second': 1.0 / max(self._step_interval, 1e-6),
                    'equity_curve': list(equity_curve),
                    'cost': 0.001 * abs(executed_delta),
                    'cumulative_buys': cumulative_buys,
                    'cumulative_sells': cumulative_sells,
                    'transaction_distribution': dict(transaction_distribution),
                    'trade_win_rate': winning_trades / max(winning_trades + losing_trades + flat_trades, 1),
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades,
                    'flat_trades': flat_trades,
                    'executed_trade': executed_trade,
                    'timestamp': timestamp,
                })

            current_sharpe = math.sin(generation / 8.0) * 1.2 + self._rng.uniform(-0.1, 0.1)
            best_sharpe = max(best_sharpe, current_sharpe)
            trade_win_rate = winning_trades / max(winning_trades + losing_trades + flat_trades, 1)

            self._on_update({
                'kind': 'generation_update',
                'generation': generation,
                'total_generations': self._total_generations,
                'current_sharpe': current_sharpe,
                'best_sharpe': best_sharpe,
                'final_balance': balance,
                'initial_balance': gen_start_balance,
                'pnl': balance - gen_start_balance,
                'trade_win_rate': max(0.0, min(1.0, trade_win_rate)),
                'transaction_distribution': dict(transaction_distribution),
                'action_counts': dict(transaction_distribution),
                'cumulative_buys': cumulative_buys,
                'cumulative_sells': cumulative_sells,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'flat_trades': flat_trades,
                'action_series': outcomes,
                'price_series': prices,
                'last_transaction': last_transaction,
            })

        self._stop_event.wait()

    def stop(self) -> None:
        self._stop_event.set()


class TrainerRunnerAdapter:
    def __init__(
        self,
        config_path: str = 'config.yaml',
        resume: bool = True,
        resume_from: str | None = None,
        on_update: Callable[[dict], None] | None = None,
    ) -> None:
        self._config_path = config_path
        self._resume = resume
        self._resume_from = resume_from
        self._trainer = None
        self._stop_requested = False
        self._on_update = on_update
        self._forwarder_thread: Thread | None = None

    def run(self) -> None:
        trainer = build_trainer_runtime(
            config_path=self._config_path,
            resume=self._resume,
            resume_from=self._resume_from,
        )
        self._trainer = trainer
        self._start_forwarder()
        if self._stop_requested:
            trainer.stop()
        trainer.run()

    def stop(self) -> None:
        self._stop_requested = True
        if self._trainer is not None:
            self._trainer.stop()

    def _start_forwarder(self) -> None:
        if self._on_update is None or self._trainer is None:
            return

        queue = getattr(self._trainer, 'update_queue', None)
        if queue is None:
            return

        def _forward() -> None:
            while not self._stop_requested:
                try:
                    payload = queue.get(timeout=0.1)
                except Exception:
                    continue
                self._on_update(payload)

        self._forwarder_thread = Thread(target=_forward, daemon=True)
        self._forwarder_thread.start()

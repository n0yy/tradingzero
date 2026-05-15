from __future__ import annotations

import json
from threading import Event

from fastapi.testclient import TestClient

from backend.app import create_app


def test_ws_receives_training_update_when_runner_publishes():
    captured_on_update: dict = {}
    started = Event()

    class _PublishingAdapter:
        def __init__(self, on_update, _resume_from=None) -> None:
            captured_on_update['fn'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    app = create_app(runner_factory_override=_PublishingAdapter)
    client = TestClient(app)

    with client.websocket_connect('/ws/runs/stream') as ws:
        client.post('/runs/start')
        assert started.wait(2.0), 'runner did not start'

        on_update = captured_on_update['fn']
        on_update(
            {
                'generation': 1,
                'total_generations': 10,
                'training_sharpe': 1.2,
                'evaluation_sharpe': 1.5,
                'best_evaluation_sharpe': 1.5,
                'final_balance': 10500.0,
                'pnl': 500.0,
                'trade_win_rate': 0.6,
                'transaction_distribution': {'buy': 3, 'sell': 3, 'no_transaction': 4},
                'cumulative_buys': 10,
                'cumulative_sells': 8,
                'winning_trades': 4,
                'losing_trades': 2,
                'flat_trades': 1,
                'initial_balance': 10000.0,
                'last_transaction': {
                    'action': 'BUY',
                    'timestamp': '2026-05-15T00:00:00Z',
                    'execution_price': 42000.0,
                    'size_percent': 0.25,
                    'position_before': 0.25,
                    'position_after': 0.5,
                    'notional_usd': 2500.0,
                    'balance_before': 10000.0,
                    'balance_after': 10500.0,
                    'fee': 10.0,
                    'realized_pnl': 0.0,
                    'unrealized_pnl_after': 500.0,
                },
            }
        )

        msg = None
        for _ in range(10):
            raw = ws.receive_text()
            parsed = json.loads(raw)
            if parsed.get('type') == 'training_update':
                msg = parsed
                break

        assert msg is not None, 'no training_update event received'
        data = msg['data']
        assert data['generation'] == 1
        assert data['training_sharpe'] == 1.2
        assert data['evaluation_sharpe'] == 1.5
        assert data['best_evaluation_sharpe'] == 1.5
        assert data['transaction_distribution'] == {'buy': 3, 'sell': 3, 'no_transaction': 4}
        assert data['last_transaction']['action'] == 'BUY'

        client.post('/runs/stop')


def test_ws_receives_step_batch_event_when_runner_publishes_step():
    captured_on_update: dict = {}
    started = Event()

    class _PublishingAdapter:
        def __init__(self, on_update, _resume_from=None) -> None:
            captured_on_update['fn'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    app = create_app(runner_factory_override=_PublishingAdapter)
    client = TestClient(app)

    with client.websocket_connect('/ws/runs/stream') as ws:
        client.post('/runs/start')
        assert started.wait(2.0), 'runner did not start'

        on_update = captured_on_update['fn']
        on_update(
            {
                'kind': 'step_batch',
                'step': 42,
                'generation': 1,
                'price': 30100.5,
                'requested_direction': 'BUY',
                'requested_size_percent': 0.25,
                'transaction_outcome': 'BUY',
                'is_transaction': True,
                'position_before': 0.17,
                'position_after': 0.42,
                'executed_delta': 0.25,
                'position': 0.42,
                'balance': 10120.0,
                'pnl': 120.0,
                'rolling_reward': 0.018,
                'steps_per_second': 412.0,
                'equity_curve': [10000.0, 10010.0, 10120.0],
                'cost': 0.001,
                'cumulative_buys': 10,
                'cumulative_sells': 8,
                'transaction_distribution': {'buy': 3, 'sell': 3, 'no_transaction': 4},
                'trade_win_rate': 0.6,
                'winning_trades': 4,
                'losing_trades': 2,
                'flat_trades': 1,
                'executed_trade': {
                    'action': 'BUY',
                    'timestamp': '2026-05-15T00:00:00Z',
                    'execution_price': 30100.5,
                    'size_percent': 0.25,
                    'position_before': 0.17,
                    'position_after': 0.42,
                    'notional_usd': 2500.0,
                    'balance_before': 10000.0,
                    'balance_after': 10120.0,
                    'fee': 10.0,
                    'realized_pnl': 0.0,
                    'unrealized_pnl_after': 30.0,
                },
            }
        )

        msg = None
        for _ in range(10):
            raw = ws.receive_text()
            parsed = json.loads(raw)
            if parsed.get('type') == 'step_batch':
                msg = parsed
                break

        assert msg is not None, 'no step_batch event received'
        data = msg['data']
        assert data['step'] == 42
        assert data['price'] == 30100.5
        assert data['transaction_outcome'] == 'BUY'
        assert data['position'] == 0.42
        assert data['equity_curve'] == [10000.0, 10010.0, 10120.0]

        client.post('/runs/stop')

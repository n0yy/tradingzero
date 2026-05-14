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
                'current_sharpe': 1.5,
                'best_sharpe': 1.5,
                'final_balance': 10500.0,
                'pnl': 500.0,
                'win_rate': 0.6,
                'action_counts': {'buy': 3, 'hold': 4, 'sell': 3},
                'cumulative_buys': 10,
                'cumulative_sells': 8,
                'action_series': [1],
                'price_series': [42000.0],
                'initial_balance': 10000.0,
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
        assert data['current_sharpe'] == 1.5
        assert data['action_distribution'] == {'buy': 3, 'hold': 4, 'sell': 3}
        assert data['last_action']['action'] == 'BUY'

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
                'last_action': 1,
                'position': 0.42,
                'balance': 10120.0,
                'pnl': 120.0,
                'rolling_reward': 0.018,
                'steps_per_second': 412.0,
                'equity_curve': [10000.0, 10010.0, 10120.0],
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
        assert data['last_action'] == 'BUY'
        assert data['position'] == 0.42
        assert data['equity_curve'] == [10000.0, 10010.0, 10120.0]

        client.post('/runs/stop')

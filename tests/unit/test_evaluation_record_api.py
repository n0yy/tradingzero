from __future__ import annotations

import json
from threading import Event

from fastapi.testclient import TestClient

from backend.app import create_app


def test_generation_evaluation_record_is_persisted_and_retrievable(tmp_path):
    captured_on_update: dict = {}
    started = Event()

    class _PublishingAdapter:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured_on_update['fn'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    db_url = f"sqlite:///{tmp_path / 'evaluation-records.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=_PublishingAdapter,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    assert start.status_code == 202
    run_id = start.json()['run_id']
    assert started.wait(2.0), 'runner did not start'

    on_update = captured_on_update['fn']
    on_update(
        {
            'generation': 2,
            'training_sharpe': 0.91,
            'evaluation_sharpe': 1.23,
            'best_evaluation_sharpe': 1.45,
            'promoted': False,
            'total_generations': 10,
            'final_balance': 10234.56,
            'pnl': 234.56,
            'initial_balance': 10000.0,
            'trade_win_rate': 0.62,
            'evaluation_executed_trade_count': 6,
            'evaluation_sell_realized_exit_count': 2,
            'promotion_gate_reasons': ['Evaluation Sharpe 1.2300 did not beat target 1.5000.'],
            'promotion_gate_checks': [
                {
                    'name': 'evaluation_sharpe_threshold',
                    'passed': False,
                    'actual': 1.23,
                    'target': 1.5,
                    'message': 'Evaluation Sharpe 1.2300 did not beat target 1.5000.',
                }
            ],
            'anchor_results': [
                {
                    'label': 'A1',
                    'start_index': 1437,
                    'start_timestamp': '2023-11-29T21:28:20+00:00',
                    'evaluation_sharpe': 1.1,
                    'executed_trade_count': 3,
                    'sell_realized_exit_count': 1,
                    'final_balance': 10100.0,
                    'pnl': 100.0,
                },
                {
                    'label': 'A2',
                    'start_index': 1499,
                    'start_timestamp': '2023-11-30T12:58:20+00:00',
                    'evaluation_sharpe': 1.36,
                    'executed_trade_count': 3,
                    'sell_realized_exit_count': 1,
                    'final_balance': 10369.12,
                    'pnl': 369.12,
                },
            ],
            'transaction_distribution': {'buy': 4, 'sell': 2, 'no_transaction': 7},
            'cumulative_buys': 20,
            'cumulative_sells': 11,
            'winning_trades': 5,
            'losing_trades': 2,
            'flat_trades': 1,
            'last_transaction': {
                'action': 'BUY',
                'timestamp': '2026-05-15T00:00:00Z',
                'execution_price': 101.0,
                'size_percent': 0.25,
                'position_before': 0.25,
                'position_after': 0.5,
                'notional_usd': 2500.0,
                'balance_before': 10000.0,
                'balance_after': 10050.0,
                'fee': 10.0,
                'realized_pnl': 0.0,
                'unrealized_pnl_after': 12.0,
            },
        }
    )

    response = client.get(f'/runs/{run_id}/evaluations')
    assert response.status_code == 200
    payload = response.json()['evaluations']
    assert len(payload) == 1

    record = payload[0]
    assert record['generation'] == 2
    assert record['evaluation_sharpe'] == 1.23
    assert record['best_evaluation_sharpe'] == 1.45
    assert record['evaluation_executed_trade_count'] == 6
    assert record['evaluation_sell_realized_exit_count'] == 2
    assert record['promoted'] is False
    assert record['promotion_gate_reasons'] == ['Evaluation Sharpe 1.2300 did not beat target 1.5000.']
    assert len(record['anchor_results']) == 2
    assert record['anchor_results'][0]['label'] == 'A1'
    assert record['anchor_results'][1]['evaluation_sharpe'] == 1.36

    client.post('/runs/stop')


def test_latest_generation_record_overwrites_same_generation_for_same_run(tmp_path):
    captured_on_update: dict = {}
    started = Event()

    class _PublishingAdapter:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured_on_update['fn'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    db_url = f"sqlite:///{tmp_path / 'evaluation-records-upsert.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=_PublishingAdapter,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    run_id = start.json()['run_id']
    assert started.wait(2.0), 'runner did not start'

    on_update = captured_on_update['fn']
    base_payload = {
        'generation': 1,
        'training_sharpe': 0.8,
        'evaluation_sharpe': 1.0,
        'best_evaluation_sharpe': 1.0,
        'promoted': False,
        'total_generations': 10,
        'final_balance': 10010.0,
        'pnl': 10.0,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.4,
        'evaluation_executed_trade_count': 4,
        'evaluation_sell_realized_exit_count': 2,
        'promotion_gate_reasons': [],
        'promotion_gate_checks': [],
        'anchor_results': [{'label': 'A1', 'evaluation_sharpe': 1.0}],
        'transaction_distribution': {'buy': 2, 'sell': 2, 'no_transaction': 8},
        'cumulative_buys': 2,
        'cumulative_sells': 2,
        'winning_trades': 1,
        'losing_trades': 1,
        'flat_trades': 0,
        'last_transaction': None,
    }

    on_update(dict(base_payload))
    updated = dict(base_payload)
    updated['evaluation_sharpe'] = 1.2
    updated['best_evaluation_sharpe'] = 1.2
    updated['promoted'] = True
    updated['promotion_gate_reasons'] = ['Evaluation Sharpe 1.2000 beat target 1.0500.']
    updated['anchor_results'] = [{'label': 'A1', 'evaluation_sharpe': 1.2}]
    on_update(updated)

    response = client.get(f'/runs/{run_id}/evaluations')
    assert response.status_code == 200
    payload = response.json()['evaluations']
    assert len(payload) == 1
    assert payload[0]['generation'] == 1
    assert payload[0]['evaluation_sharpe'] == 1.2
    assert payload[0]['promoted'] is True
    assert payload[0]['anchor_results'][0]['evaluation_sharpe'] == 1.2

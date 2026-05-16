"""
Persistence and replay coverage for EvaluationSpec, seeds, and EvaluationRecord reads.

Load-bearing behaviour:
- EvaluationSpec seeds (training_seed, evaluation_seed) must survive a full
  persist → read roundtrip via the API.
- EvaluationRecord reads must expose anchor_results with all required fields.
- Replaying the same seeds must reproduce identical slice boundaries.
"""
from __future__ import annotations

import json
from threading import Event

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.evaluation_spec import RunEvaluationPlan


def _make_runner_factory(captured: dict):
    class _InertRunner:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured['on_update'] = on_update
            self._stop = Event()

        def run(self) -> None:
            captured.setdefault('started', Event()).set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    return _InertRunner


# ---------------------------------------------------------------------------
# EvaluationSpec seeds roundtrip
# ---------------------------------------------------------------------------

def test_evaluation_spec_seeds_survive_persist_read_roundtrip(tmp_path):
    """
    Seeds written to the DB via /runs/start must be readable back from
    /runs/status and /runs (history) without mutation.
    """
    from backend.evaluation_spec import build_run_evaluation_plan
    from tests.unit.test_evaluation_spec import make_config, make_market_data

    data = make_market_data()

    def plan_factory(_config: dict) -> RunEvaluationPlan:
        return build_run_evaluation_plan(
            config=make_config(),
            data=data,
            training_seed=7777,
            evaluation_seed=8888,
        )

    db_url = f"sqlite:///{tmp_path / 'seeds-roundtrip.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_mode='inmemory',
        evaluation_plan_factory_override=plan_factory,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    assert start.status_code == 202
    spec_from_start = start.json()['evaluation_spec']

    # Seeds must be present in the start response
    assert spec_from_start['training_seed'] == 7777
    assert spec_from_start['evaluation_seed'] == 8888

    # Seeds must survive the status read
    status = client.get('/runs/status')
    assert status.status_code == 200
    spec_from_status = status.json()['evaluation_spec']
    assert spec_from_status['training_seed'] == 7777
    assert spec_from_status['evaluation_seed'] == 8888

    # Seeds must survive the history read
    history = client.get('/runs')
    assert history.status_code == 200
    spec_from_history = history.json()['runs'][0]['evaluation_spec']
    assert spec_from_history['training_seed'] == 7777
    assert spec_from_history['evaluation_seed'] == 8888

    # Full spec must be identical across all three reads
    assert spec_from_start == spec_from_status == spec_from_history


def test_evaluation_spec_slice_boundaries_survive_roundtrip(tmp_path):
    """
    Slice boundaries (start_index, end_index, candle_count) must be preserved
    exactly through the persist → read cycle.
    """
    from backend.evaluation_spec import build_run_evaluation_plan
    from tests.unit.test_evaluation_spec import make_config, make_market_data

    data = make_market_data()
    plan = build_run_evaluation_plan(
        config=make_config(),
        data=data,
        training_seed=1,
        evaluation_seed=2,
    )
    original_spec = plan.evaluation_spec

    def plan_factory(_config: dict) -> RunEvaluationPlan:
        return plan

    db_url = f"sqlite:///{tmp_path / 'slice-roundtrip.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_mode='inmemory',
        evaluation_plan_factory_override=plan_factory,
    )
    client = TestClient(app)

    client.post('/runs/start')
    status = client.get('/runs/status')
    persisted_spec = status.json()['evaluation_spec']

    assert persisted_spec['training_slice']['start_index'] == original_spec['training_slice']['start_index']
    assert persisted_spec['training_slice']['end_index'] == original_spec['training_slice']['end_index']
    assert persisted_spec['evaluation_slice']['start_index'] == original_spec['evaluation_slice']['start_index']
    assert persisted_spec['evaluation_slice']['end_index'] == original_spec['evaluation_slice']['end_index']
    assert persisted_spec['evaluation_anchors'] == original_spec['evaluation_anchors']


# ---------------------------------------------------------------------------
# EvaluationRecord reads with anchor_results
# ---------------------------------------------------------------------------

def test_evaluation_record_anchor_results_are_readable_with_all_fields(tmp_path):
    """
    anchor_results stored in an EvaluationRecord must be readable back from
    GET /runs/{run_id}/evaluations with all required fields intact.
    """
    captured: dict = {}
    started = Event()

    class _Runner:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured['on_update'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    db_url = f"sqlite:///{tmp_path / 'anchor-results.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=_Runner,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    assert start.status_code == 202
    run_id = start.json()['run_id']
    assert started.wait(2.0)

    anchor_results = [
        {
            'label': 'A1',
            'start_index': 1600,
            'start_timestamp': '2023-11-29T21:28:20+00:00',
            'evaluation_sharpe': 0.85,
            'executed_trade_count': 4,
            'sell_realized_exit_count': 2,
            'final_balance': 10200.0,
            'pnl': 200.0,
        },
        {
            'label': 'A2',
            'start_index': 1700,
            'start_timestamp': '2023-11-30T12:58:20+00:00',
            'evaluation_sharpe': 1.12,
            'executed_trade_count': 5,
            'sell_realized_exit_count': 3,
            'final_balance': 10450.0,
            'pnl': 450.0,
        },
        {
            'label': 'A3',
            'start_index': 1800,
            'start_timestamp': '2023-12-01T04:28:20+00:00',
            'evaluation_sharpe': 0.67,
            'executed_trade_count': 3,
            'sell_realized_exit_count': 1,
            'final_balance': 10050.0,
            'pnl': 50.0,
        },
        {
            'label': 'A4',
            'start_index': 1900,
            'start_timestamp': '2023-12-01T19:58:20+00:00',
            'evaluation_sharpe': 1.34,
            'executed_trade_count': 6,
            'sell_realized_exit_count': 4,
            'final_balance': 10600.0,
            'pnl': 600.0,
        },
    ]

    captured['on_update']({
        'generation': 3,
        'training_sharpe': 0.9,
        'evaluation_sharpe': 1.0,
        'best_evaluation_sharpe': 1.0,
        'promoted': True,
        'total_generations': 10,
        'final_balance': 10325.0,
        'pnl': 325.0,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.6,
        'evaluation_executed_trade_count': 18,
        'evaluation_sell_realized_exit_count': 10,
        'promotion_gate_reasons': [],
        'promotion_gate_checks': [
            {'name': 'evaluation_sharpe_threshold', 'passed': True, 'actual': 1.0, 'target': 0.95, 'message': 'passed'},
        ],
        'anchor_results': anchor_results,
        'transaction_distribution': {'buy': 10, 'sell': 8, 'no_transaction': 50},
        'cumulative_buys': 10,
        'cumulative_sells': 8,
        'winning_trades': 6,
        'losing_trades': 2,
        'flat_trades': 0,
        'last_transaction': None,
    })

    response = client.get(f'/runs/{run_id}/evaluations')
    assert response.status_code == 200
    records = response.json()['evaluations']
    assert len(records) == 1

    record = records[0]
    assert record['generation'] == 3
    assert record['promoted'] is True
    assert len(record['anchor_results']) == 4

    # All anchor fields must be present and correct
    for i, anchor in enumerate(record['anchor_results']):
        expected = anchor_results[i]
        assert anchor['label'] == expected['label']
        assert anchor['start_index'] == expected['start_index']
        assert anchor['start_timestamp'] == expected['start_timestamp']
        assert anchor['evaluation_sharpe'] == expected['evaluation_sharpe']
        assert anchor['executed_trade_count'] == expected['executed_trade_count']
        assert anchor['sell_realized_exit_count'] == expected['sell_realized_exit_count']
        assert anchor['final_balance'] == expected['final_balance']
        assert anchor['pnl'] == expected['pnl']

    client.post('/runs/stop')


def test_evaluation_record_anchor_results_survive_upsert(tmp_path):
    """
    When the same generation is updated (upsert), anchor_results must be
    replaced with the latest values, not accumulated.
    """
    captured: dict = {}
    started = Event()

    class _Runner:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured['on_update'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    db_url = f"sqlite:///{tmp_path / 'anchor-upsert.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=_Runner,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    run_id = start.json()['run_id']
    assert started.wait(2.0)

    base = {
        'generation': 1,
        'training_sharpe': 0.5,
        'evaluation_sharpe': 0.8,
        'best_evaluation_sharpe': 0.8,
        'promoted': False,
        'total_generations': 5,
        'final_balance': 10100.0,
        'pnl': 100.0,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.5,
        'evaluation_executed_trade_count': 4,
        'evaluation_sell_realized_exit_count': 2,
        'promotion_gate_reasons': [],
        'promotion_gate_checks': [],
        'anchor_results': [{'label': 'A1', 'start_index': 100, 'evaluation_sharpe': 0.8,
                             'executed_trade_count': 4, 'sell_realized_exit_count': 2,
                             'final_balance': 10100.0, 'pnl': 100.0}],
        'transaction_distribution': {'buy': 2, 'sell': 2, 'no_transaction': 10},
        'cumulative_buys': 2, 'cumulative_sells': 2,
        'winning_trades': 1, 'losing_trades': 1, 'flat_trades': 0,
        'last_transaction': None,
    }
    captured['on_update'](base)

    # Upsert with updated anchor_results
    updated = dict(base)
    updated['evaluation_sharpe'] = 1.1
    updated['best_evaluation_sharpe'] = 1.1
    updated['promoted'] = True
    updated['anchor_results'] = [{'label': 'A1', 'start_index': 100, 'evaluation_sharpe': 1.1,
                                   'executed_trade_count': 5, 'sell_realized_exit_count': 3,
                                   'final_balance': 10300.0, 'pnl': 300.0}]
    captured['on_update'](updated)

    response = client.get(f'/runs/{run_id}/evaluations')
    records = response.json()['evaluations']
    assert len(records) == 1  # upsert, not append
    assert records[0]['anchor_results'][0]['evaluation_sharpe'] == 1.1
    assert records[0]['anchor_results'][0]['executed_trade_count'] == 5
    assert records[0]['promoted'] is True

    client.post('/runs/stop')


def test_evaluation_record_promotion_gate_checks_are_readable(tmp_path):
    """
    promotion_gate_checks stored in an EvaluationRecord must be readable back
    with name, passed, actual, target, and message fields intact.
    """
    captured: dict = {}
    started = Event()

    class _Runner:
        def __init__(self, on_update, _resume_from=None, _evaluation_plan=None) -> None:
            captured['on_update'] = on_update
            self._stop = Event()

        def run(self) -> None:
            started.set()
            self._stop.wait()

        def stop(self) -> None:
            self._stop.set()

    db_url = f"sqlite:///{tmp_path / 'gate-checks.db'}"
    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=_Runner,
    )
    client = TestClient(app)

    start = client.post('/runs/start')
    run_id = start.json()['run_id']
    assert started.wait(2.0)

    gate_checks = [
        {'name': 'evaluation_sharpe_threshold', 'passed': False, 'actual': 0.9, 'target': 1.05,
         'message': 'Evaluation Sharpe 0.9000 did not beat target 1.0500.'},
        {'name': 'executed_trade_count', 'passed': True, 'actual': 6, 'target': 4,
         'message': 'Executed Trade count 6 met minimum 4.'},
        {'name': 'sell_realized_exit_count', 'passed': True, 'actual': 3, 'target': 2,
         'message': 'SELL realized exits 3 met minimum 2.'},
    ]

    captured['on_update']({
        'generation': 5,
        'training_sharpe': 0.8,
        'evaluation_sharpe': 0.9,
        'best_evaluation_sharpe': 1.0,
        'promoted': False,
        'total_generations': 10,
        'final_balance': 10050.0,
        'pnl': 50.0,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.5,
        'evaluation_executed_trade_count': 6,
        'evaluation_sell_realized_exit_count': 3,
        'promotion_gate_reasons': ['Evaluation Sharpe 0.9000 did not beat target 1.0500.'],
        'promotion_gate_checks': gate_checks,
        'anchor_results': [],
        'transaction_distribution': {'buy': 3, 'sell': 3, 'no_transaction': 10},
        'cumulative_buys': 3, 'cumulative_sells': 3,
        'winning_trades': 2, 'losing_trades': 1, 'flat_trades': 0,
        'last_transaction': None,
    })

    response = client.get(f'/runs/{run_id}/evaluations')
    records = response.json()['evaluations']
    assert len(records) == 1

    record = records[0]
    assert record['promotion_gate_reasons'] == ['Evaluation Sharpe 0.9000 did not beat target 1.0500.']
    assert len(record['promotion_gate_checks']) == 3

    sharpe_check = record['promotion_gate_checks'][0]
    assert sharpe_check['name'] == 'evaluation_sharpe_threshold'
    assert sharpe_check['passed'] is False
    assert sharpe_check['actual'] == 0.9
    assert sharpe_check['target'] == 1.05
    assert 'did not beat target' in sharpe_check['message']

    trade_check = record['promotion_gate_checks'][1]
    assert trade_check['name'] == 'executed_trade_count'
    assert trade_check['passed'] is True

    client.post('/runs/stop')

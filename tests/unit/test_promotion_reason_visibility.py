"""
Coverage for promotion pass/fail reason visibility in backend outputs.

Load-bearing behaviour:
- map_training_payload must preserve promotion_gate_reasons as a list of strings
- map_training_payload must preserve promotion_gate_checks with name/passed/actual/target/message
- A failed gate check must produce a non-empty promotion_gate_reasons list
- A passed promotion must produce promoted=True with empty promotion_gate_reasons
- The SSE event emitted by the backend must include promotion_gate_reasons and
  promotion_gate_checks so the frontend can render pass/fail decisions
"""
from __future__ import annotations

from backend.event_mapper import map_training_payload


def _base_payload(**overrides) -> dict:
    base = {
        'generation': 1,
        'training_sharpe': 0.8,
        'evaluation_sharpe': 0.9,
        'best_evaluation_sharpe': 1.0,
        'promoted': False,
        'evaluation_executed_trade_count': 6,
        'evaluation_sell_realized_exit_count': 3,
        'promotion_gate_reasons': [],
        'promotion_gate_checks': [],
        'final_balance': 10000.0,
        'pnl': 0.0,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.5,
        'total_generations': 10,
        'transaction_distribution': {'buy': 3, 'sell': 3, 'no_transaction': 10},
        'cumulative_buys': 3,
        'cumulative_sells': 3,
        'winning_trades': 2,
        'losing_trades': 1,
        'flat_trades': 0,
        'last_transaction': None,
    }
    base.update(overrides)
    return base


def test_promotion_gate_reasons_are_preserved_in_sse_event():
    """
    promotion_gate_reasons must appear verbatim in the mapped SSE event data.
    """
    reasons = [
        'Evaluation Sharpe 0.9000 did not beat target 1.0500.',
        'Executed Trade count 1 was below minimum 4.',
    ]
    event = map_training_payload(_base_payload(promotion_gate_reasons=reasons))

    assert event['type'] == 'training_update'
    assert event['data']['promotion_gate_reasons'] == reasons


def test_promotion_gate_checks_are_preserved_in_sse_event():
    """
    promotion_gate_checks must appear in the mapped SSE event with all fields.
    """
    checks = [
        {
            'name': 'evaluation_sharpe_threshold',
            'passed': False,
            'actual': 0.9,
            'target': 1.05,
            'message': 'Evaluation Sharpe 0.9000 did not beat target 1.0500.',
        },
        {
            'name': 'executed_trade_count',
            'passed': True,
            'actual': 6,
            'target': 4,
            'message': 'Executed Trade count 6 met minimum 4.',
        },
        {
            'name': 'sell_realized_exit_count',
            'passed': True,
            'actual': 3,
            'target': 2,
            'message': 'SELL realized exits 3 met minimum 2.',
        },
    ]
    event = map_training_payload(_base_payload(promotion_gate_checks=checks))

    data = event['data']
    assert len(data['promotion_gate_checks']) == 3

    sharpe_check = data['promotion_gate_checks'][0]
    assert sharpe_check['name'] == 'evaluation_sharpe_threshold'
    assert sharpe_check['passed'] is False
    assert sharpe_check['actual'] == 0.9
    assert sharpe_check['target'] == 1.05
    assert 'did not beat target' in sharpe_check['message']

    trade_check = data['promotion_gate_checks'][1]
    assert trade_check['name'] == 'executed_trade_count'
    assert trade_check['passed'] is True
    assert trade_check['actual'] == 6


def test_failed_promotion_has_non_empty_reasons_and_promoted_false():
    """
    When promoted=False, promotion_gate_reasons must be non-empty and
    promoted must be False in the SSE event.
    """
    event = map_training_payload(_base_payload(
        promoted=False,
        promotion_gate_reasons=['Evaluation Sharpe 0.9000 did not beat target 1.0500.'],
        promotion_gate_checks=[
            {'name': 'evaluation_sharpe_threshold', 'passed': False, 'actual': 0.9, 'target': 1.05,
             'message': 'Evaluation Sharpe 0.9000 did not beat target 1.0500.'},
        ],
    ))

    data = event['data']
    assert data['promoted'] is False
    assert len(data['promotion_gate_reasons']) > 0
    assert any('did not beat target' in r for r in data['promotion_gate_reasons'])


def test_successful_promotion_has_empty_reasons_and_promoted_true():
    """
    When promoted=True, promotion_gate_reasons must be empty and
    promoted must be True in the SSE event.
    """
    event = map_training_payload(_base_payload(
        promoted=True,
        evaluation_sharpe=1.2,
        best_evaluation_sharpe=1.2,
        promotion_gate_reasons=[],
        promotion_gate_checks=[
            {'name': 'evaluation_sharpe_threshold', 'passed': True, 'actual': 1.2, 'target': 1.05,
             'message': 'Evaluation Sharpe 1.2000 beat target 1.0500.'},
            {'name': 'executed_trade_count', 'passed': True, 'actual': 6, 'target': 4,
             'message': 'Executed Trade count 6 met minimum 4.'},
            {'name': 'sell_realized_exit_count', 'passed': True, 'actual': 3, 'target': 2,
             'message': 'SELL realized exits 3 met minimum 2.'},
        ],
    ))

    data = event['data']
    assert data['promoted'] is True
    assert data['promotion_gate_reasons'] == []
    assert all(check['passed'] for check in data['promotion_gate_checks'])


def test_activity_gate_failure_reason_is_visible_in_sse_event():
    """
    When the activity gate fails (too few trades), the reason must be visible
    in the SSE event so the frontend can display it.
    """
    event = map_training_payload(_base_payload(
        promoted=False,
        evaluation_executed_trade_count=1,
        evaluation_sell_realized_exit_count=0,
        promotion_gate_reasons=[
            'Executed Trade count 1 was below minimum 4.',
            'SELL realized exits 0 were below minimum 2.',
        ],
        promotion_gate_checks=[
            {'name': 'evaluation_sharpe_threshold', 'passed': True, 'actual': 1.2, 'target': 1.05,
             'message': 'Evaluation Sharpe 1.2000 beat target 1.0500.'},
            {'name': 'executed_trade_count', 'passed': False, 'actual': 1, 'target': 4,
             'message': 'Executed Trade count 1 was below minimum 4.'},
            {'name': 'sell_realized_exit_count', 'passed': False, 'actual': 0, 'target': 2,
             'message': 'SELL realized exits 0 were below minimum 2.'},
        ],
    ))

    data = event['data']
    assert data['promoted'] is False
    assert data['evaluation_executed_trade_count'] == 1
    assert data['evaluation_sell_realized_exit_count'] == 0

    reasons = data['promotion_gate_reasons']
    assert any('Executed Trade count 1 was below minimum' in r for r in reasons)
    assert any('SELL realized exits 0 were below minimum' in r for r in reasons)

    failed_checks = [c for c in data['promotion_gate_checks'] if not c['passed']]
    assert len(failed_checks) == 2
    failed_names = {c['name'] for c in failed_checks}
    assert 'executed_trade_count' in failed_names
    assert 'sell_realized_exit_count' in failed_names


def test_promotion_gate_reasons_are_empty_list_when_not_provided():
    """
    When promotion_gate_reasons is absent from the payload, the SSE event
    must emit an empty list (not None or missing).
    """
    payload = _base_payload()
    del payload['promotion_gate_reasons']
    del payload['promotion_gate_checks']

    event = map_training_payload(payload)
    data = event['data']
    assert data['promotion_gate_reasons'] == []
    assert data['promotion_gate_checks'] == []


def test_promotion_gate_check_passed_field_is_boolean():
    """
    The passed field in each gate check must be a Python bool, not an int.
    This ensures the frontend can use strict equality checks.
    """
    checks = [
        {'name': 'evaluation_sharpe_threshold', 'passed': True, 'actual': 1.2, 'target': 1.05,
         'message': 'passed'},
        {'name': 'executed_trade_count', 'passed': False, 'actual': 1, 'target': 4,
         'message': 'failed'},
    ]
    event = map_training_payload(_base_payload(promotion_gate_checks=checks))

    for check in event['data']['promotion_gate_checks']:
        assert isinstance(check['passed'], bool), f"passed must be bool, got {type(check['passed'])}"

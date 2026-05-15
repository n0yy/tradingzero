from backend.event_mapper import map_step_batch_payload, map_training_payload


def test_event_mapper_produces_typed_payload_with_last_transaction_fields():
    payload = {
        'generation': 3,
        'training_sharpe': 0.91,
        'evaluation_sharpe': 1.23,
        'best_evaluation_sharpe': 1.45,
        'promoted': False,
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
            },
            {
                'name': 'executed_trade_count',
                'passed': True,
                'actual': 6,
                'target': 4,
                'message': 'Executed Trade count 6 met minimum 4.',
            },
        ],
        'final_balance': 10234.56,
        'pnl': 234.56,
        'initial_balance': 10000.0,
        'trade_win_rate': 0.62,
        'total_generations': 10,
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

    event = map_training_payload(payload)

    assert event['type'] == 'training_update'
    data = event['data']
    assert data['training_sharpe'] == 0.91
    assert data['evaluation_sharpe'] == 1.23
    assert data['best_evaluation_sharpe'] == 1.45
    assert data['promoted'] is False
    assert data['evaluation_executed_trade_count'] == 6
    assert data['evaluation_sell_realized_exit_count'] == 2
    assert data['promotion_gate_reasons'] == ['Evaluation Sharpe 1.2300 did not beat target 1.5000.']
    assert data['promotion_gate_checks'][0]['name'] == 'evaluation_sharpe_threshold'
    assert data['promotion_gate_checks'][0]['passed'] is False
    assert data['transaction_distribution']['buy'] == 4
    assert data['transaction_distribution']['no_transaction'] == 7

    last_transaction = data['last_transaction']
    assert last_transaction['action'] in {'BUY', 'SELL'}
    required = {
        'timestamp',
        'execution_price',
        'size_percent',
        'position_before',
        'position_after',
        'notional_usd',
        'balance_before',
        'balance_after',
        'fee',
        'realized_pnl',
        'unrealized_pnl_after',
    }
    assert required.issubset(set(last_transaction.keys()))


def test_step_batch_mapper_emits_high_frequency_event():
    payload = {
        'step': 1234,
        'generation': 3,
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
        'cumulative_buys': 20,
        'cumulative_sells': 11,
        'transaction_distribution': {'buy': 4, 'sell': 2, 'no_transaction': 7},
        'trade_win_rate': 0.62,
        'winning_trades': 5,
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

    event = map_step_batch_payload(payload)

    assert event['type'] == 'step_batch'
    data = event['data']
    assert data['step'] == 1234
    assert data['generation'] == 3
    assert data['price'] == 30100.5
    assert data['requested_direction'] == 'BUY'
    assert data['transaction_outcome'] == 'BUY'
    assert data['position'] == 0.42
    assert data['balance'] == 10120.0
    assert data['pnl'] == 120.0
    assert data['rolling_reward'] == 0.018
    assert data['steps_per_second'] == 412.0
    assert data['equity_curve'] == [10000.0, 10010.0, 10120.0]
    assert data['executed_trade']['action'] == 'BUY'
    assert 'timestamp' in data

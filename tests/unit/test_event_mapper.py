from backend.event_mapper import map_step_batch_payload, map_training_payload


def test_event_mapper_produces_typed_payload_with_last_action_fields():
    payload = {
        'generation': 3,
        'current_sharpe': 1.23,
        'best_sharpe': 1.45,
        'final_balance': 10234.56,
        'pnl': 234.56,
        'initial_balance': 10000.0,
        'win_rate': 0.62,
        'total_generations': 10,
        'action_counts': {'buy': 4, 'hold': 7, 'sell': 2},
        'cumulative_buys': 20,
        'cumulative_sells': 11,
        'price_series': [100.0, 101.0],
        'action_series': [1, 0],
    }

    event = map_training_payload(payload)

    assert event['type'] == 'training_update'
    data = event['data']
    assert data['current_sharpe'] == 1.23
    assert data['best_sharpe'] == 1.45
    assert data['action_distribution']['buy'] == 4

    last_action = data['last_action']
    assert last_action['action'] in {'BUY', 'SELL', 'HOLD'}
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
        'unrealized_pnl_after',
    }
    assert required.issubset(set(last_action.keys()))


def test_step_batch_mapper_emits_high_frequency_event():
    payload = {
        'step': 1234,
        'generation': 3,
        'price': 30100.5,
        'last_action': 1,
        'position': 0.42,
        'balance': 10120.0,
        'pnl': 120.0,
        'rolling_reward': 0.018,
        'steps_per_second': 412.0,
        'equity_curve': [10000.0, 10010.0, 10120.0],
    }

    event = map_step_batch_payload(payload)

    assert event['type'] == 'step_batch'
    data = event['data']
    assert data['step'] == 1234
    assert data['generation'] == 3
    assert data['price'] == 30100.5
    assert data['last_action'] in {'BUY', 'SELL', 'HOLD'}
    assert data['position'] == 0.42
    assert data['balance'] == 10120.0
    assert data['pnl'] == 120.0
    assert data['rolling_reward'] == 0.018
    assert data['steps_per_second'] == 412.0
    assert data['equity_curve'] == [10000.0, 10010.0, 10120.0]
    assert 'timestamp' in data


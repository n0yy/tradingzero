from fastapi.testclient import TestClient

from backend.app import create_app


def _config_payload(checkpoint_dir: str) -> dict:
    return {
        'data': {
            'exchange': 'binance',
            'symbol': 'BTC/USDT',
            'timeframe': '15m',
            'window_size': 60,
        },
        'env': {
            'initial_balance': 10000,
            'transaction_cost': 0.001,
            'episode_length': 500,
        },
        'agent': {
            'learning_rate': 0.0001,
            'n_steps': 4096,
            'batch_size': 128,
            'clip_range': 0.2,
            'total_episodes': 1000,
            'promote_threshold': 0.05,
        },
        'self_play': {
            'checkpoint_interval': 10,
            'checkpoint_dir': checkpoint_dir,
        },
    }


def _battle_result() -> dict:
    return {
        'checkpoint': 'agent/checkpoints/best.zip',
        'symbol': 'BTC/USDT',
        'timeframe': '15m',
        'initial_balance': 10000.0,
        'final_balance': 10100.0,
        'pnl': 100.0,
        'pnl_pct': 0.01,
        'total_steps': 500,
        'total_trades': 12,
        'trade_win_rate': 0.6,
        'winning_trades': 3,
        'losing_trades': 2,
        'flat_trades': 0,
        'transaction_distribution': {'buy': 5, 'sell': 4, 'no_transaction': 491},
        'price_series': [100.0, 101.0],
        'equity_curve': [10000.0, 10100.0],
        'executed_trades': [],
    }


def test_battle_best_returns_runtime_result(tmp_path, mocker):
    checkpoint_dir = tmp_path / 'checkpoints'
    checkpoint_dir.mkdir()
    (checkpoint_dir / 'best.zip').write_bytes(b'zip')

    db_url = f"sqlite:///{tmp_path / 'battle.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    client.put('/config/active', json=_config_payload(str(checkpoint_dir)))
    mocker.patch('backend.app.run_battle', return_value=_battle_result())

    response = client.post('/battle/best')

    assert response.status_code == 200
    data = response.json()
    assert data['checkpoint'] == 'agent/checkpoints/best.zip'
    assert data['trade_win_rate'] == 0.6


def test_battle_best_returns_404_when_best_checkpoint_missing(tmp_path):
    checkpoint_dir = tmp_path / 'checkpoints'
    checkpoint_dir.mkdir()

    db_url = f"sqlite:///{tmp_path / 'battle.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    client.put('/config/active', json=_config_payload(str(checkpoint_dir)))
    response = client.post('/battle/best')

    assert response.status_code == 404
    assert response.json()['detail']['error']['code'] == 'checkpoint_not_found'


def test_battle_best_returns_409_for_incompatible_checkpoint(tmp_path, mocker):
    checkpoint_dir = tmp_path / 'checkpoints'
    checkpoint_dir.mkdir()
    (checkpoint_dir / 'best.zip').write_bytes(b'zip')

    db_url = f"sqlite:///{tmp_path / 'battle.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    client.put('/config/active', json=_config_payload(str(checkpoint_dir)))
    mocker.patch('backend.app.run_battle', side_effect=ValueError('obs space mismatch'))

    response = client.post('/battle/best')

    assert response.status_code == 409
    assert response.json()['detail']['error']['code'] == 'checkpoint_incompatible'

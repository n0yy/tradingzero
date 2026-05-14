from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


def test_run_and_config_persist_across_app_restart(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'app.db'}"
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(
        '\n'.join(
            [
                'data:',
                '  exchange: binance',
                '  symbol: BTC/USDT',
                '  timeframe: 15m',
                '  window_size: 60',
                'env:',
                '  initial_balance: 10000',
                '  transaction_cost: 0.001',
                '  episode_length: 500',
                'agent:',
                '  learning_rate: 0.0001',
                '  n_steps: 4096',
                '  batch_size: 128',
                '  clip_range: 0.2',
                '  total_episodes: 1000',
                '  promote_threshold: 0.05',
                'self_play:',
                '  checkpoint_interval: 10',
                '  checkpoint_dir: agent/checkpoints/',
                '',
            ]
        ),
        encoding='utf-8',
    )

    app1 = create_app(database_url=db_url, config_path=str(config_path), runner_mode='inmemory')
    client1 = TestClient(app1)

    start = client1.post('/runs/start')
    assert start.status_code == 202
    run_id = start.json()['run_id']

    app2 = create_app(database_url=db_url, config_path=str(config_path), runner_mode='inmemory')
    client2 = TestClient(app2)

    status = client2.get('/runs/status')
    assert status.status_code == 200
    assert status.json()['run_id'] == run_id

    config = client2.get('/config/active')
    assert config.status_code == 200
    assert config.json()['config']['data']['symbol'] == 'BTC/USDT'


def test_running_run_is_marked_interrupted_on_app_restart(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'app.db'}"
    app1 = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client1 = TestClient(app1)

    start = client1.post('/runs/start')
    assert start.status_code == 202
    run_id = start.json()['run_id']

    app2 = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client2 = TestClient(app2)

    status = client2.get('/runs/status')
    assert status.status_code == 200
    assert status.json()['run_id'] == run_id
    assert status.json()['state'] == 'error'
    assert status.json()['error'] == 'run interrupted by backend restart'


def test_events_queryable_per_run(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'app.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    start = client.post('/runs/start')
    run_id = start.json()['run_id']
    client.post('/runs/stop')

    events = client.get(f'/runs/{run_id}/events')
    assert events.status_code == 200
    payload = events.json()['events']
    assert len(payload) >= 2
    assert any(item['type'] == 'running' for item in payload)

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


class _Runner:
    def run(self):
        return None

    def stop(self):
        return None


def test_updated_active_config_is_used_when_starting_new_run(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'cfg-startup.db'}"

    fallback_checkpoint_dir = tmp_path / 'fallback-checkpoints'
    fallback_checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (fallback_checkpoint_dir / 'best.zip').write_bytes(b'fallback')

    db_checkpoint_dir = tmp_path / 'db-checkpoints'
    db_checkpoint_dir.mkdir(parents=True, exist_ok=True)

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
                f'  checkpoint_dir: {fallback_checkpoint_dir}',
                '  checkpoint_interval: 10',
                '',
            ]
        ),
        encoding='utf-8',
    )

    app = create_app(
        database_url=db_url,
        config_path=str(config_path),
        runner_factory_override=lambda _on_update, _resume_from=None: _Runner(),
    )
    client = TestClient(app)

    new_payload = {
        'data': {
            'exchange': 'okx',
            'symbol': 'ETH/USDT',
            'timeframe': '1h',
            'window_size': 72,
        },
        'env': {
            'initial_balance': 25000,
            'transaction_cost': 0.002,
            'episode_length': 800,
        },
        'agent': {
            'learning_rate': 0.0002,
            'n_steps': 2048,
            'batch_size': 64,
            'clip_range': 0.15,
            'total_episodes': 777,
            'promote_threshold': 0.07,
        },
        'self_play': {
            'checkpoint_interval': 12,
            'checkpoint_dir': str(db_checkpoint_dir),
        },
    }

    save = client.put('/config/active', json=new_payload)
    assert save.status_code == 200
    revision_version = save.json()['version']

    start = client.post('/runs/start')
    assert start.status_code == 202
    run_id = start.json()['run_id']

    active = client.get('/config/active')
    assert active.status_code == 200
    assert active.json()['version'] == revision_version
    assert active.json()['config']['data']['exchange'] == 'okx'
    assert active.json()['config']['self_play']['checkpoint_dir'] == str(db_checkpoint_dir)

    events = client.get(f'/runs/{run_id}/events')
    assert events.status_code == 200
    assert any(item['message'] == 'run started' for item in events.json()['events'])

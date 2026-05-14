from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


def _safe_payload(checkpoint_dir: str = 'agent/checkpoints/') -> dict:
    return {
        'data': {
            'exchange': 'binance',
            'symbol': 'ETH/USDT',
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


def test_config_update_and_read_roundtrip(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'config-api.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    payload = _safe_payload()
    put = client.put('/config/active', json=payload)
    assert put.status_code == 200
    body = put.json()
    assert body['version']
    assert body['config']['data']['symbol'] == 'ETH/USDT'

    get = client.get('/config/active')
    assert get.status_code == 200
    assert get.json()['version'] == body['version']
    assert get.json()['config']['data']['symbol'] == 'ETH/USDT'


def test_config_update_rejects_invalid_payload(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'config-invalid.db'}"
    app = create_app(database_url=db_url, config_path=str(tmp_path / 'missing.yaml'), runner_mode='inmemory')
    client = TestClient(app)

    payload = _safe_payload()
    payload['env']['transaction_cost'] = -0.5

    put = client.put('/config/active', json=payload)
    assert put.status_code == 422


def test_retry_uses_checkpoint_dir_from_db_active_config(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'config-retry.db'}"

    wrong_dir = tmp_path / 'wrong-checkpoints'
    wrong_dir.mkdir(parents=True, exist_ok=True)
    (wrong_dir / 'best.zip').write_bytes(b'wrong')

    right_dir = tmp_path / 'right-checkpoints'
    right_dir.mkdir(parents=True, exist_ok=True)
    target = right_dir / 'gen_0001.zip'
    target.write_bytes(b'right')

    config_path = tmp_path / 'config.yaml'
    config_path.write_text(
        'self_play:\n  checkpoint_dir: ' + str(wrong_dir) + '\n',
        encoding='utf-8',
    )

    seen: list[str | None] = []

    class _Runner:
        def run(self):
            return None

        def stop(self):
            return None

    def runner_factory(_on_update, resume_from=None):
        seen.append(resume_from)
        return _Runner()

    app = create_app(
        database_url=db_url,
        config_path=str(config_path),
        runner_factory_override=runner_factory,
    )
    client = TestClient(app)

    payload = _safe_payload(checkpoint_dir=str(right_dir))
    save = client.put('/config/active', json=payload)
    assert save.status_code == 200

    retry = client.post('/runs/retry')
    assert retry.status_code == 202
    assert seen[-1] == str(target)

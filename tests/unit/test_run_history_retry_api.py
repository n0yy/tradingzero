from __future__ import annotations

from pathlib import Path
import time
from fastapi.testclient import TestClient

from backend.app import create_app


def test_runs_history_lists_latest_first(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'history.db'}"
    config_path = tmp_path / 'config.yaml'
    config_path.write_text('self_play:\n  checkpoint_dir: agent/checkpoints\n', encoding='utf-8')

    app = create_app(database_url=db_url, config_path=str(config_path), runner_mode='inmemory')
    client = TestClient(app)

    first = client.post('/runs/start')
    assert first.status_code == 202
    client.post('/runs/stop')

    second = client.post('/runs/start')
    assert second.status_code == 202
    client.post('/runs/stop')

    res = client.get('/runs')
    assert res.status_code == 200
    runs = res.json()['runs']
    assert len(runs) >= 2
    assert runs[0]['run_id'] == second.json()['run_id']
    assert runs[1]['run_id'] == first.json()['run_id']


def test_retry_uses_latest_checkpoint_and_starts_new_run(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'retry.db'}"
    checkpoint_dir = tmp_path / 'checkpoints'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    older = checkpoint_dir / 'best.zip'
    older.write_bytes(b'old')
    time.sleep(0.01)
    newer = checkpoint_dir / 'gen_0004.zip'
    newer.write_bytes(b'new')

    config_path = tmp_path / 'config.yaml'
    config_path.write_text(f'self_play:\n  checkpoint_dir: {checkpoint_dir}\n', encoding='utf-8')

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

    res = client.post('/runs/retry')
    assert res.status_code == 202
    assert res.json()['state'] in {'running', 'done'}
    assert seen[-1] == str(newer)


def test_retry_returns_conflict_when_checkpoint_missing(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'retry-empty.db'}"
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(f'self_play:\n  checkpoint_dir: {tmp_path / "missing-checkpoints"}\n', encoding='utf-8')

    app = create_app(database_url=db_url, config_path=str(config_path), runner_mode='inmemory')
    client = TestClient(app)

    res = client.post('/runs/retry')
    assert res.status_code == 409
    assert res.json()['detail']['error']['code'] == 'checkpoint_not_found'

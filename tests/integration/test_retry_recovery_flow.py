from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import create_app


class _ConditionalRunner:
    def __init__(self, should_fail: bool):
        self._should_fail = should_fail

    def run(self):
        if self._should_fail:
            raise RuntimeError('forced crash before retry')
        return None

    def stop(self):
        return None


def test_retry_recovery_flow_uses_latest_checkpoint_and_records_history(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'integration-retry.db'}"
    checkpoint_dir = tmp_path / 'checkpoints'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    older = checkpoint_dir / 'best.zip'
    older.write_bytes(b'old-best')
    time.sleep(0.01)
    newer = checkpoint_dir / 'gen_0010.zip'
    newer.write_bytes(b'newer-gen')

    config_path = tmp_path / 'config.yaml'
    config_path.write_text(f'self_play:\n  checkpoint_dir: {checkpoint_dir}\n', encoding='utf-8')

    seen_resume_from: list[str | None] = []

    def runner_factory(_on_update, resume_from=None):
        seen_resume_from.append(resume_from)
        return _ConditionalRunner(should_fail=resume_from is None)

    app = create_app(
        database_url=db_url,
        config_path=str(config_path),
        runner_factory_override=runner_factory,
    )
    client = TestClient(app)

    first = client.post('/runs/start')
    assert first.status_code == 202
    first_run_id = first.json()['run_id']

    first_status = None
    for _ in range(40):
        first_status = client.get('/runs/status').json()
        if first_status['state'] == 'error':
            break
        time.sleep(0.02)

    assert first_status is not None
    assert first_status['state'] == 'error'

    retry = client.post('/runs/retry')
    assert retry.status_code == 202
    retry_run_id = retry.json()['run_id']
    assert retry_run_id != first_run_id

    retry_status = None
    for _ in range(40):
        retry_status = client.get('/runs/status').json()
        history_payload = client.get('/runs').json()['runs']
        retry_row = next((item for item in history_payload if item['run_id'] == retry_run_id), None)
        if (
            retry_status['run_id'] == retry_run_id
            and retry_status['state'] in {'running', 'done'}
            and retry_row is not None
            and retry_row['state'] in {'running', 'done'}
        ):
            break
        time.sleep(0.02)

    assert retry_status is not None
    assert retry_status['run_id'] == retry_run_id
    history_payload = client.get('/runs').json()['runs']
    retry_row = next((item for item in history_payload if item['run_id'] == retry_run_id), None)
    assert retry_row is not None
    assert retry_row['state'] in {'running', 'done'}

    assert seen_resume_from[-1] == str(newer)

    history = client.get('/runs')
    assert history.status_code == 200
    runs = history.json()['runs']
    assert len(runs) >= 2
    assert runs[0]['run_id'] == retry_run_id
    assert runs[1]['run_id'] == first_run_id

    retry_events = client.get(f'/runs/{retry_run_id}/events')
    assert retry_events.status_code == 200
    messages = [item['message'] for item in retry_events.json()['events']]
    assert any('run retried from' in msg for msg in messages)

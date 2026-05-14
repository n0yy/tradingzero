from fastapi.testclient import TestClient

from backend.app import create_app


class _FailRunner:
    def run(self):
        raise RuntimeError('boom failure')

    def stop(self):
        return None


def test_runtime_error_persisted_as_run_error(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'error.db'}"

    app = create_app(
        database_url=db_url,
        config_path=str(tmp_path / 'missing.yaml'),
        runner_factory_override=lambda _on_update: _FailRunner(),
    )
    client = TestClient(app)

    start_res = client.post('/runs/start')
    assert start_res.status_code == 202
    run_id = start_res.json()['run_id']

    for _ in range(20):
        status = client.get('/runs/status').json()
        if status['state'] == 'error':
            break

    assert status['state'] == 'error'

    errors = client.get(f'/runs/{run_id}/errors')
    assert errors.status_code == 200
    payload = errors.json()['errors']
    assert any(item['code'] == 'runtime_error' for item in payload)
    assert any('boom failure' in item['message'] for item in payload)

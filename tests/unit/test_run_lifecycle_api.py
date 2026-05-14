from fastapi.testclient import TestClient

from backend.app import create_app


def test_start_changes_status_to_running():
    app = create_app(runner_mode='inmemory')
    client = TestClient(app)

    start_res = client.post('/runs/start')
    assert start_res.status_code == 202

    status_res = client.get('/runs/status')
    assert status_res.status_code == 200
    body = status_res.json()
    assert body['state'] in {'running', 'stopping', 'done'}


def test_second_start_returns_conflict_when_active_run():
    app = create_app(runner_mode='inmemory')
    client = TestClient(app)

    first = client.post('/runs/start')
    assert first.status_code == 202

    second = client.post('/runs/start')
    assert second.status_code == 409
    assert second.json()['detail']['error']['code'] == 'active_run'


def test_stop_requests_graceful_shutdown():
    app = create_app(runner_mode='inmemory')
    client = TestClient(app)

    client.post('/runs/start')
    stop_res = client.post('/runs/stop')

    assert stop_res.status_code == 202
    assert stop_res.json()['state'] in {'stopping', 'done'}

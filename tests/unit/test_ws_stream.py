from fastapi.testclient import TestClient

from backend.app import create_app


def test_ws_connect_disconnect_does_not_crash_app():
    app = create_app(runner_mode='inmemory')
    client = TestClient(app)

    with client.websocket_connect('/ws/runs/stream') as ws:
        assert ws is not None

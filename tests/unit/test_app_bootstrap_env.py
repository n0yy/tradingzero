import importlib

from fastapi.testclient import TestClient


def test_app_uses_inmemory_runner_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv('TRADINGZERO_RUNNER_MODE', 'inmemory')
    monkeypatch.setenv('TRADINGZERO_DATABASE_URL', f"sqlite:///{tmp_path / 'env-app.db'}")
    monkeypatch.setenv('TRADINGZERO_CONFIG_PATH', 'missing.yaml')

    import backend.app as app_module

    app_module = importlib.reload(app_module)
    client = TestClient(app_module.app)

    start = client.post('/runs/start')
    assert start.status_code == 202
    stop = client.post('/runs/stop')
    assert stop.status_code == 202

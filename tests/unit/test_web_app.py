from fastapi.testclient import TestClient


def test_healthz_returns_ok_payload():
    from backend.app import app

    client = TestClient(app)
    response = client.get('/healthz')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

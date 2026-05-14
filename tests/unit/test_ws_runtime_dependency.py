from __future__ import annotations

import importlib


def test_websocket_runtime_dependency_is_importable():
    """Regression: backend WS endpoints return 404 when uvicorn boots without
    a WebSocket implementation library available. We declare `websockets` in
    pyproject.toml — this test fails fast if it ever drops out of the lock."""
    try:
        importlib.import_module('websockets')
        return
    except ImportError:
        pass

    try:
        importlib.import_module('wsproto')
    except ImportError as exc:
        raise AssertionError(
            'Neither `websockets` nor `wsproto` is installed. Uvicorn will reject '
            'WebSocket upgrades with HTTP 404, breaking /ws/runs/stream.'
        ) from exc

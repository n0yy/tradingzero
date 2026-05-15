from __future__ import annotations

import os
from pathlib import Path
from typing import Callable
import asyncio
from queue import Empty

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from backend.battle_runtime import run_battle
from backend.lifecycle import ActiveRunError, NoActiveRunError, RunController
from backend.event_bus import TrainingEventBus
from backend.event_mapper import map_step_batch_payload, map_training_payload
from backend.persistence.db import build_engine, build_session_factory
from backend.persistence.models import Base
from backend.run_lifecycle_module import RunLifecycleModule
from backend.runners import InMemoryRunnerAdapter, TrainerRunnerAdapter
from backend.runners import RunnerAdapter
from backend.schemas import (
    ActiveConfigResponse,
    BattleResultResponse,
    EventListResponse,
    HealthResponse,
    RunHistoryResponse,
    RunErrorListResponse,
    RunStatusResponse,
    SafeConfigPayload,
)

DEFAULT_DB_URL = 'sqlite:///data/tradingzero.db'
DEFAULT_CONFIG_PATH = 'config.yaml'
DEFAULT_RUNNER_MODE = 'trainer'


def create_app(
    database_url: str = DEFAULT_DB_URL,
    config_path: str = DEFAULT_CONFIG_PATH,
    runner_mode: str = DEFAULT_RUNNER_MODE,
    runner_factory_override: Callable[..., RunnerAdapter] | None = None,
) -> FastAPI:
    app = FastAPI(title='TradingZero API')
    event_bus = TrainingEventBus()

    if database_url.startswith('sqlite:///'):
        db_file = Path(database_url.replace('sqlite:///', '', 1))
        db_file.parent.mkdir(parents=True, exist_ok=True)

    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    Base.metadata.create_all(bind=engine)

    def on_training_update(payload: dict) -> None:
        kind = payload.get('kind', 'generation_update')
        if kind == 'step_batch':
            event = map_step_batch_payload(payload)
        else:
            event = map_training_payload(payload)
        event_bus.publish(event)

    if runner_factory_override is not None:
        def build_override(resume_from: str | None) -> RunnerAdapter:
            try:
                return runner_factory_override(on_training_update, resume_from)
            except TypeError:
                return runner_factory_override(on_training_update)

        runner_factory = lambda: build_override(None)
        runner_factory_with_resume = lambda resume_from: build_override(resume_from)
    else:
        if runner_mode == 'trainer':
            runner_factory = lambda: TrainerRunnerAdapter(config_path=config_path, resume=True, on_update=on_training_update)
            runner_factory_with_resume = lambda resume_from: TrainerRunnerAdapter(
                config_path=config_path,
                resume=True,
                resume_from=resume_from,
                on_update=on_training_update,
            )
        elif runner_mode == 'inmemory':
            runner_factory = lambda: InMemoryRunnerAdapter(on_update=on_training_update)
            runner_factory_with_resume = lambda _resume_from: InMemoryRunnerAdapter(on_update=on_training_update)
        else:
            raise ValueError(f'Unsupported runner_mode: {runner_mode}')

    controller = RunController(runner_factory=runner_factory)
    module = RunLifecycleModule(
        controller=controller,
        session_factory=session_factory,
        config_path=config_path,
        retention_days=90,
        runner_factory_with_resume=runner_factory_with_resume,
    )
    controller.set_state_listener(module.persist_state)
    module.mark_interrupted_runs()

    @app.get('/healthz', response_model=HealthResponse)
    def healthz() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/runs/status', response_model=RunStatusResponse)
    def get_run_status() -> dict[str, str | None]:
        return module.status()

    @app.post('/runs/start', status_code=202, response_model=RunStatusResponse)
    def start_run() -> dict[str, str | None]:
        try:
            return module.start()
        except ActiveRunError:
            raise HTTPException(
                status_code=409,
                detail={'error': {'code': 'active_run', 'message': 'run already active'}},
            )

    @app.post('/runs/stop', status_code=202, response_model=RunStatusResponse)
    def stop_run() -> dict[str, str | None]:
        try:
            return module.stop()
        except NoActiveRunError:
            raise HTTPException(
                status_code=409,
                detail={'error': {'code': 'no_active_run', 'message': 'no run is active'}},
            )

    @app.get('/runs/{run_id}/events', response_model=EventListResponse)
    def list_run_events(run_id: str) -> dict[str, list[dict[str, str]]]:
        return module.list_events(run_id)

    @app.get('/runs/{run_id}/errors', response_model=RunErrorListResponse)
    def list_run_errors(run_id: str) -> dict[str, list[dict[str, str | None]]]:
        return module.list_errors(run_id)

    @app.get('/runs', response_model=RunHistoryResponse)
    def list_runs() -> dict[str, list[dict[str, str | None]]]:
        return module.list_runs()

    @app.post('/runs/retry', status_code=202, response_model=RunStatusResponse)
    def retry_run() -> dict[str, str | None]:
        try:
            return module.retry()
        except ActiveRunError:
            raise HTTPException(
                status_code=409,
                detail={'error': {'code': 'active_run', 'message': 'run already active'}},
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=409,
                detail={'error': {'code': 'checkpoint_not_found', 'message': 'no compatible checkpoint found'}},
            )

    @app.get('/config/active', response_model=ActiveConfigResponse)
    def active_config() -> dict[str, str | None]:
        return module.active_config()

    @app.put('/config/active', response_model=ActiveConfigResponse)
    def update_active_config(payload: SafeConfigPayload) -> dict[str, str | None]:
        return module.set_active_config(payload.model_dump())

    @app.post('/battle/best', response_model=BattleResultResponse)
    def run_best_battle() -> dict:
        checkpoint = module.best_checkpoint_path()
        if checkpoint is None:
            raise HTTPException(
                status_code=404,
                detail={'error': {'code': 'checkpoint_not_found', 'message': 'best.zip not found'}},
            )

        config = module._active_config_payload()
        try:
            return run_battle(checkpoint=checkpoint, config=config)
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail={'error': {'code': 'checkpoint_incompatible', 'message': str(exc)}},
            ) from exc

    @app.websocket('/ws/runs/stream')
    async def ws_runs_stream(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = event_bus.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.to_thread(queue.get, True, 1.0)
                    await websocket.send_json(event)
                except Empty:
                    await websocket.send_json({'type': 'keepalive'})
        except WebSocketDisconnect:
            pass
        finally:
            event_bus.unsubscribe(queue)

    return app


app = create_app(
    database_url=os.getenv('TRADINGZERO_DATABASE_URL', DEFAULT_DB_URL),
    config_path=os.getenv('TRADINGZERO_CONFIG_PATH', DEFAULT_CONFIG_PATH),
    runner_mode=os.getenv('TRADINGZERO_RUNNER_MODE', DEFAULT_RUNNER_MODE),
)

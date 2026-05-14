from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock, Thread
from typing import Callable, Literal

from backend.runners import InMemoryRunnerAdapter, RunnerAdapter

RunState = Literal['idle', 'running', 'stopping', 'done', 'error']


@dataclass
class RunStatus:
    state: RunState = 'idle'
    run_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class ActiveRunError(Exception):
    pass


class NoActiveRunError(Exception):
    pass


class RunController:
    def __init__(
        self,
        on_state_change: Callable[[RunStatus], None] | None = None,
        runner_factory: Callable[[], RunnerAdapter] | None = None,
    ) -> None:
        self._lock = Lock()
        self._status = RunStatus()
        self._thread: Thread | None = None
        self._runner: RunnerAdapter | None = None
        self._on_state_change = on_state_change
        self._runner_factory = runner_factory or InMemoryRunnerAdapter

    def set_state_listener(self, listener: Callable[[RunStatus], None] | None) -> None:
        self._on_state_change = listener

    def status(self) -> RunStatus:
        with self._lock:
            return RunStatus(**self._status.__dict__)

    def start(self, runner_factory_override: Callable[[], RunnerAdapter] | None = None) -> RunStatus:
        with self._lock:
            if self._status.state in {'running', 'stopping'}:
                raise ActiveRunError('run is already active')

            run_id = datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')
            self._status = RunStatus(
                state='running',
                run_id=run_id,
                started_at=datetime.now(UTC).isoformat(),
                finished_at=None,
                error=None,
            )
            self._runner = (runner_factory_override or self._runner_factory)()
            self._thread = Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            status = RunStatus(**self._status.__dict__)
        self._emit(status)
        return status

    def stop(self) -> RunStatus:
        with self._lock:
            if self._status.state not in {'running', 'stopping'}:
                raise NoActiveRunError('no active run')
            if self._runner is not None:
                self._status.state = 'stopping'
                self._runner.stop()
            status = RunStatus(**self._status.__dict__)
        self._emit(status)
        return status

    def _run_loop(self) -> None:
        runner = self._runner
        if runner is None:
            return

        try:
            runner.run()
            with self._lock:
                self._status.state = 'done'
                self._status.finished_at = datetime.now(UTC).isoformat()
                status = RunStatus(**self._status.__dict__)
            self._emit(status)
        except Exception as exc:  # pragma: no cover
            with self._lock:
                self._status.state = 'error'
                self._status.error = str(exc)
                self._status.finished_at = datetime.now(UTC).isoformat()
                status = RunStatus(**self._status.__dict__)
            self._emit(status)

    def _emit(self, status: RunStatus) -> None:
        if self._on_state_change is None:
            return
        self._on_state_change(status)

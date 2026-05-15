from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable
import json
import yaml

from backend.lifecycle import ActiveRunError, NoActiveRunError, RunController, RunStatus
from backend.persistence.repository import Repository
from backend.runners import RunnerAdapter
from backend.schemas import SafeConfigPayload


@dataclass
class RunLifecycleModule:
    controller: RunController
    session_factory: object
    config_path: str = 'config.yaml'
    retention_days: int = 90
    runner_factory_with_resume: Callable[[str | None], RunnerAdapter] | None = None

    def _default_safe_config(self) -> dict:
        return {
            'data': {
                'exchange': 'binance',
                'symbol': 'BTC/USDT',
                'timeframe': '15m',
                'window_size': 60,
            },
            'env': {
                'initial_balance': 10000,
                'transaction_cost': 0.001,
                'episode_length': 500,
            },
            'agent': {
                'learning_rate': 1e-4,
                'n_steps': 4096,
                'batch_size': 128,
                'clip_range': 0.2,
                'total_episodes': 1000,
                'promote_threshold': 0.05,
            },
            'self_play': {
                'checkpoint_interval': 10,
                'checkpoint_dir': 'agent/checkpoints/',
            },
        }

    def _config_from_file(self) -> dict:
        path = Path(self.config_path)
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}

    def _extract_safe_config(self, payload: dict) -> dict:
        base = self._default_safe_config()
        for key in ('data', 'env', 'agent', 'self_play'):
            src = payload.get(key, {})
            if isinstance(src, dict):
                base[key] = {**base[key], **src}
        return base

    def _active_config_payload(self) -> dict:
        with self.session_factory() as session:
            revision = Repository(session).active_config()
            if revision is not None:
                try:
                    raw = json.loads(revision.payload)
                except json.JSONDecodeError:
                    raw = yaml.safe_load(revision.payload) or {}
                normalized = self._extract_safe_config(raw if isinstance(raw, dict) else {})
                return SafeConfigPayload.model_validate(normalized).model_dump()
        file_cfg = self._extract_safe_config(self._config_from_file())
        return SafeConfigPayload.model_validate(file_cfg).model_dump()

    def _to_payload(self, status: RunStatus) -> dict[str, str | None]:
        return {
            'state': status.state,
            'run_id': status.run_id,
            'started_at': status.started_at,
            'finished_at': status.finished_at,
            'error': status.error,
        }

    def status(self) -> dict[str, str | None]:
        status = self.controller.status()
        if status.run_id is not None:
            return self._to_payload(status)

        with self.session_factory() as session:
            latest = Repository(session).latest_run()
            if latest is None:
                return self._to_payload(status)
            return {
                'state': latest.state,
                'run_id': latest.id,
                'started_at': latest.started_at.isoformat() if latest.started_at else None,
                'finished_at': latest.finished_at.isoformat() if latest.finished_at else None,
                'error': latest.error_message,
            }

    def mark_interrupted_runs(self) -> None:
        with self.session_factory() as session:
            Repository(session).mark_active_runs_interrupted()
            session.commit()

    def start(
        self,
        retry_from: str | None = None,
    ) -> dict[str, str | None]:
        config_obj = self._active_config_payload()
        config_payload = json.dumps(config_obj, sort_keys=True)
        runner_factory_override = None
        if retry_from is not None and self.runner_factory_with_resume is not None:
            runner_factory_override = lambda: self.runner_factory_with_resume(retry_from)
        try:
            status = self.controller.start(runner_factory_override=runner_factory_override)
        except ActiveRunError:
            raise

        with self.session_factory() as session:
            repo = Repository(session)
            revision = repo.upsert_config_revision(config_payload)
            repo.create_run(status.run_id or datetime.now(UTC).isoformat(), status.state, revision.id)
            if retry_from is None:
                repo.add_event(status.run_id or '', 'running', 'run started')
            else:
                repo.add_event(status.run_id or '', 'running', f'run retried from {retry_from}')
            repo.prune_older_than_days(self.retention_days)
            session.commit()

        return self._to_payload(status)

    def stop(self) -> dict[str, str | None]:
        try:
            status = self.controller.stop()
        except NoActiveRunError:
            raise
        return self._to_payload(status)

    def persist_state(self, status: RunStatus) -> None:
        if status.run_id is None:
            return
        with self.session_factory() as session:
            repo = Repository(session)
            updated = repo.update_run_state(status.run_id, status.state, status.error)
            if updated is None:
                repo.create_run(status.run_id, status.state, None)
                repo.update_run_state(status.run_id, status.state, status.error)
            if status.state in {'running', 'stopping', 'done', 'error'}:
                repo.add_event(status.run_id, status.state, f'run state -> {status.state}')
            if status.state == 'error' and status.error:
                repo.add_error(status.run_id, code='runtime_error', message=status.error)
            session.commit()

    def list_events(self, run_id: str) -> dict[str, list[dict[str, str]]]:
        with self.session_factory() as session:
            events = Repository(session).list_events(run_id)
            return {
                'events': [
                    {
                        'type': event.type,
                        'message': event.message,
                        'created_at': event.created_at.isoformat(),
                    }
                    for event in events
                ]
            }

    def list_errors(self, run_id: str) -> dict[str, list[dict[str, str | None]]]:
        with self.session_factory() as session:
            errors = Repository(session).list_errors(run_id)
            return {
                'errors': [
                    {
                        'code': err.code,
                        'message': err.message,
                        'details': err.details,
                        'created_at': err.created_at.isoformat(),
                    }
                    for err in errors
                ]
            }

    def list_runs(self) -> dict[str, list[dict[str, str | None]]]:
        with self.session_factory() as session:
            runs = Repository(session).list_runs()
            return {
                'runs': [
                    {
                        'run_id': run.id,
                        'state': run.state,
                        'started_at': run.started_at.isoformat() if run.started_at else None,
                        'finished_at': run.finished_at.isoformat() if run.finished_at else None,
                        'error': run.error_message,
                    }
                    for run in runs
                ]
            }

    def latest_checkpoint_path(self) -> str | None:
        payload = self._active_config_payload()
        checkpoint_dir = Path(payload['self_play']['checkpoint_dir'])

        candidates = []
        best = checkpoint_dir / 'best.zip'
        if best.exists():
            candidates.append(best)
        candidates.extend(sorted(checkpoint_dir.glob('gen_*.zip')))

        if not candidates:
            return None
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(latest)

    def best_checkpoint_path(self) -> str | None:
        payload = self._active_config_payload()
        checkpoint_dir = Path(payload['self_play']['checkpoint_dir'])
        best = checkpoint_dir / 'best.zip'
        if not best.exists():
            return None
        return str(best)

    def retry(self) -> dict[str, str | None]:
        checkpoint = self.latest_checkpoint_path()
        if checkpoint is None:
            raise FileNotFoundError('no compatible checkpoint found')
        return self.start(retry_from=checkpoint)

    def active_config(self) -> dict[str, str | None]:
        with self.session_factory() as session:
            revision = Repository(session).active_config()
            if revision is None:
                return {'version': None, 'config': None, 'created_at': None}
            try:
                raw = json.loads(revision.payload)
            except json.JSONDecodeError:
                raw = yaml.safe_load(revision.payload) or {}
            payload = SafeConfigPayload.model_validate(self._extract_safe_config(raw if isinstance(raw, dict) else {}))
            return {
                'version': revision.version,
                'config': payload.model_dump(),
                'created_at': revision.created_at.isoformat(),
            }

    def set_active_config(self, payload: dict) -> dict[str, str | None]:
        safe = SafeConfigPayload.model_validate(payload)
        serial = json.dumps(safe.model_dump(), sort_keys=True)
        with self.session_factory() as session:
            repo = Repository(session)
            revision = repo.upsert_config_revision(serial)
            session.commit()
            return {
                'version': revision.version,
                'config': safe.model_dump(),
                'created_at': revision.created_at.isoformat(),
            }

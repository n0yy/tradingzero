from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.persistence.models import ConfigRevision, Run, RunError, RunEvaluationRecord, RunEvent


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_config_revision(self, payload: str) -> ConfigRevision:
        version = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        existing = self.session.scalar(select(ConfigRevision).where(ConfigRevision.version == version))
        if existing is not None:
            return existing
        row = ConfigRevision(version=version, payload=payload, created_at=datetime.now(UTC))
        self.session.add(row)
        self.session.flush()
        return row

    def create_run(
        self,
        run_id: str,
        state: str,
        config_revision_id: int | None,
        evaluation_spec: dict | None = None,
    ) -> Run:
        existing = self.session.get(Run, run_id)
        if existing is not None:
            existing.state = state
            if existing.config_revision_id is None:
                existing.config_revision_id = config_revision_id
            if existing.evaluation_spec_payload is None and evaluation_spec is not None:
                existing.evaluation_spec_payload = json.dumps(evaluation_spec, sort_keys=True)
            self.session.flush()
            return existing
        row = Run(
            id=run_id,
            state=state,
            started_at=datetime.now(UTC),
            config_revision_id=config_revision_id,
            evaluation_spec_payload=json.dumps(evaluation_spec, sort_keys=True) if evaluation_spec is not None else None,
        )
        self.session.add(row)
        try:
            self.session.flush()
            return row
        except IntegrityError:
            self.session.rollback()
            existing = self.session.get(Run, run_id)
            if existing is None:
                raise
            existing.state = state
            if existing.config_revision_id is None:
                existing.config_revision_id = config_revision_id
            if existing.evaluation_spec_payload is None and evaluation_spec is not None:
                existing.evaluation_spec_payload = json.dumps(evaluation_spec, sort_keys=True)
            self.session.flush()
            return existing

    def update_run_state(self, run_id: str, state: str, error_message: str | None = None) -> Run | None:
        row = self.session.get(Run, run_id)
        if row is None:
            return None
        row.state = state
        row.error_message = error_message
        if state in {'done', 'error'}:
            row.finished_at = datetime.now(UTC)
        self.session.flush()
        return row

    def add_event(self, run_id: str, event_type: str, message: str) -> RunEvent:
        row = RunEvent(run_id=run_id, type=event_type, message=message, created_at=datetime.now(UTC))
        self.session.add(row)
        self.session.flush()
        return row

    def add_error(self, run_id: str, code: str, message: str, details: str | None = None) -> RunError:
        row = RunError(run_id=run_id, code=code, message=message, details=details, created_at=datetime.now(UTC))
        self.session.add(row)
        self.session.flush()
        return row

    def upsert_evaluation_record(self, run_id: str, payload: dict) -> RunEvaluationRecord:
        generation = int(payload.get('generation', 0))
        existing = self.session.scalar(
            select(RunEvaluationRecord).where(
                RunEvaluationRecord.run_id == run_id,
                RunEvaluationRecord.generation == generation,
            )
        )
        row = existing or RunEvaluationRecord(
            run_id=run_id,
            generation=generation,
            training_sharpe=0.0,
            evaluation_sharpe=0.0,
            best_evaluation_sharpe=0.0,
            promoted=0,
            evaluation_executed_trade_count=0,
            evaluation_sell_realized_exit_count=0,
            promotion_gate_reasons_payload='[]',
            promotion_gate_checks_payload='[]',
            anchor_results_payload='[]',
            created_at=datetime.now(UTC),
        )
        row.training_sharpe = float(payload.get('training_sharpe', 0.0))
        row.evaluation_sharpe = float(payload.get('evaluation_sharpe', 0.0))
        row.best_evaluation_sharpe = float(payload.get('best_evaluation_sharpe', 0.0))
        row.promoted = 1 if bool(payload.get('promoted', False)) else 0
        row.evaluation_executed_trade_count = int(payload.get('evaluation_executed_trade_count', 0))
        row.evaluation_sell_realized_exit_count = int(payload.get('evaluation_sell_realized_exit_count', 0))
        row.promotion_gate_reasons_payload = json.dumps(payload.get('promotion_gate_reasons') or [], sort_keys=True)
        row.promotion_gate_checks_payload = json.dumps(payload.get('promotion_gate_checks') or [], sort_keys=True)
        row.anchor_results_payload = json.dumps(payload.get('anchor_results') or [], sort_keys=True)
        if existing is None:
            self.session.add(row)
        self.session.flush()
        return row

    def list_events(self, run_id: str) -> list[RunEvent]:
        return list(self.session.scalars(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.id.asc())))

    def list_errors(self, run_id: str) -> list[RunError]:
        return list(self.session.scalars(select(RunError).where(RunError.run_id == run_id).order_by(RunError.id.asc())))

    def list_evaluation_records(self, run_id: str) -> list[RunEvaluationRecord]:
        return list(
            self.session.scalars(
                select(RunEvaluationRecord)
                .where(RunEvaluationRecord.run_id == run_id)
                .order_by(RunEvaluationRecord.generation.asc())
            )
        )

    def latest_evaluation_record(self, run_id: str) -> RunEvaluationRecord | None:
        return self.session.scalar(
            select(RunEvaluationRecord)
            .where(RunEvaluationRecord.run_id == run_id)
            .order_by(RunEvaluationRecord.generation.desc())
            .limit(1)
        )

    def latest_run(self) -> Run | None:
        return self.session.scalar(select(Run).order_by(Run.started_at.desc()))

    def mark_active_runs_interrupted(self) -> int:
        runs = list(self.session.scalars(select(Run).where(Run.state.in_(['running', 'stopping']))))
        now = datetime.now(UTC)
        for run in runs:
            run.state = 'error'
            run.error_message = 'run interrupted by backend restart'
            run.finished_at = now
            self.add_event(run.id, 'error', 'run interrupted by backend restart')
            self.add_error(run.id, code='runtime_interrupted', message='run interrupted by backend restart')
        self.session.flush()
        return len(runs)

    def list_runs(self, limit: int = 50) -> list[Run]:
        stmt = select(Run).order_by(Run.started_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def active_config(self) -> ConfigRevision | None:
        return self.session.scalar(select(ConfigRevision).order_by(ConfigRevision.created_at.desc()))

    def prune_older_than_days(self, days: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)

        old_run_ids = [
            row[0]
            for row in self.session.execute(
                select(Run.id).where(Run.started_at.is_not(None), Run.started_at < cutoff)
            ).all()
        ]
        if not old_run_ids:
            return 0

        self.session.execute(delete(RunEvent).where(RunEvent.run_id.in_(old_run_ids)))
        self.session.execute(delete(RunError).where(RunError.run_id.in_(old_run_ids)))
        self.session.execute(delete(RunEvaluationRecord).where(RunEvaluationRecord.run_id.in_(old_run_ids)))
        self.session.execute(delete(Run).where(Run.id.in_(old_run_ids)))
        self.session.flush()
        return len(old_run_ids)

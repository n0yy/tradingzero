from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = 'runs'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_revision_id: Mapped[int | None] = mapped_column(ForeignKey('config_revisions.id'), nullable=True)
    evaluation_spec_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list['RunEvent']] = relationship(back_populates='run', cascade='all, delete-orphan')
    errors: Mapped[list['RunError']] = relationship(back_populates='run', cascade='all, delete-orphan')
    evaluation_records: Mapped[list['RunEvaluationRecord']] = relationship(
        back_populates='run',
        cascade='all, delete-orphan',
    )


class RunEvent(Base):
    __tablename__ = 'run_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[Run] = relationship(back_populates='events')


class RunError(Base):
    __tablename__ = 'run_errors'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[Run] = relationship(back_populates='errors')


class RunEvaluationRecord(Base):
    __tablename__ = 'run_evaluation_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('runs.id'), nullable=False, index=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    training_sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    evaluation_sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    best_evaluation_sharpe: Mapped[float] = mapped_column(Float, nullable=False)
    promoted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluation_executed_trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluation_sell_realized_exit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    promotion_gate_reasons_payload: Mapped[str] = mapped_column(Text, nullable=False, default='[]')
    promotion_gate_checks_payload: Mapped[str] = mapped_column(Text, nullable=False, default='[]')
    anchor_results_payload: Mapped[str] = mapped_column(Text, nullable=False, default='[]')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[Run] = relationship(back_populates='evaluation_records')


class ConfigRevision(Base):
    __tablename__ = 'config_revisions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'config_revisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version'),
        if_not_exists=True,
    )

    op.create_table(
        'runs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('state', sa.String(length=16), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('config_revision_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['config_revision_id'], ['config_revisions.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    op.create_table(
        'run_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index(op.f('ix_run_events_run_id'), 'run_events', ['run_id'], unique=False, if_not_exists=True)

    op.create_table(
        'run_errors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index(op.f('ix_run_errors_run_id'), 'run_errors', ['run_id'], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_run_errors_run_id'), table_name='run_errors')
    op.drop_table('run_errors')
    op.drop_index(op.f('ix_run_events_run_id'), table_name='run_events')
    op.drop_table('run_events')
    op.drop_table('runs')
    op.drop_table('config_revisions')

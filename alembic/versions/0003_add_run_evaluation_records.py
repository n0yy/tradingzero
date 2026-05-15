"""add run evaluation records

Revision ID: 0003_add_run_evaluation_records
Revises: 0002_add_run_evaluation_spec
Create Date: 2026-05-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '0003_add_run_evaluation_records'
down_revision = '0002_add_run_evaluation_spec'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'run_evaluation_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=64), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('training_sharpe', sa.Float(), nullable=False),
        sa.Column('evaluation_sharpe', sa.Float(), nullable=False),
        sa.Column('best_evaluation_sharpe', sa.Float(), nullable=False),
        sa.Column('promoted', sa.Integer(), nullable=False),
        sa.Column('evaluation_executed_trade_count', sa.Integer(), nullable=False),
        sa.Column('evaluation_sell_realized_exit_count', sa.Integer(), nullable=False),
        sa.Column('promotion_gate_reasons_payload', sa.Text(), nullable=False),
        sa.Column('promotion_gate_checks_payload', sa.Text(), nullable=False),
        sa.Column('anchor_results_payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id']),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index(
        op.f('ix_run_evaluation_records_run_id'),
        'run_evaluation_records',
        ['run_id'],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_run_evaluation_records_run_id'), table_name='run_evaluation_records')
    op.drop_table('run_evaluation_records')

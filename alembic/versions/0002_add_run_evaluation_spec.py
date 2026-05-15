"""add run evaluation spec payload

Revision ID: 0002_add_run_evaluation_spec
Revises: 0001_initial
Create Date: 2026-05-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '0002_add_run_evaluation_spec'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('runs', sa.Column('evaluation_spec_payload', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('runs', 'evaluation_spec_payload')

"""add stopped status to runstatus enum

Revision ID: 006
Revises: 005
Create Date: 2026-04-01
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE runstatus ADD VALUE IF NOT EXISTS 'stopped'")


def downgrade():
    # Postgres does not support removing enum values; no-op
    pass

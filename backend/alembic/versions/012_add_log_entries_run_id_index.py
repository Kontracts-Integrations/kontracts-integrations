"""add index on log_entries.run_id

Logs are almost always filtered by run (run detail view, per-run stats). The
foreign key does not create an index on Postgres, so queries filtering by run_id
did a sequential scan. Add the index.

Revision ID: 012
Revises: 011
Create Date: 2026-07-05
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_log_entries_run_id", "log_entries", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_log_entries_run_id", table_name="log_entries")

"""add bulk_batch_size to mapping_templates

Makes the bulk-publish chunk size (records per bulk API request) configurable per
mapping template instead of the hardcoded 1000.

Revision ID: 013
Revises: 012
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column("bulk_batch_size", sa.Integer(), nullable=False, server_default="1000"),
    )


def downgrade() -> None:
    op.drop_column("mapping_templates", "bulk_batch_size")

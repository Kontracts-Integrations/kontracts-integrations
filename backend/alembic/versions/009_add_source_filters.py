"""add source record filters to mapping_templates

Adds source_filters (JSONB list of {field, operator, value}) and filter_match
("all"/"any") so a mapping can restrict which source records are synced.

Revision ID: 009
Revises: 008
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column("source_filters", JSONB(), nullable=True),
    )
    op.add_column(
        "mapping_templates",
        sa.Column(
            "filter_match", sa.String(10), nullable=False, server_default="all"
        ),
    )


def downgrade() -> None:
    op.drop_column("mapping_templates", "filter_match")
    op.drop_column("mapping_templates", "source_filters")

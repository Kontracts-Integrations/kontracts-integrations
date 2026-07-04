"""add named lookup table support

Adds a `lookup_table_name` to mapping_templates (the named table a mapping
writes its produced IDs into) and a `table_name` partition column to
lease_mappings so ID lookups can be namespaced per named table.

Revision ID: 007
Revises: 006
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column("lookup_table_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "lease_mappings",
        sa.Column(
            "table_name",
            sa.String(255),
            nullable=False,
            server_default="lease_mappings",
        ),
    )
    op.create_index(
        "ix_lease_mappings_table_name", "lease_mappings", ["table_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_lease_mappings_table_name", "lease_mappings")
    op.drop_column("lease_mappings", "table_name")
    op.drop_column("mapping_templates", "lookup_table_name")

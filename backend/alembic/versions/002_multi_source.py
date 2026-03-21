"""Add multi-source IWMS support

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend the connectiontype enum with new source system values
    op.execute("ALTER TYPE connectiontype ADD VALUE IF NOT EXISTS 'sap_re'")
    op.execute("ALTER TYPE connectiontype ADD VALUE IF NOT EXISTS 'planon'")
    op.execute("ALTER TYPE connectiontype ADD VALUE IF NOT EXISTS 'costar'")
    op.execute("ALTER TYPE connectiontype ADD VALUE IF NOT EXISTS 'servicenow_wsd'")

    # Rename tririga_module -> source_object
    op.alter_column("mapping_templates", "tririga_module", new_column_name="source_object")
    # Rename tririga_query_name -> source_query
    op.alter_column("mapping_templates", "tririga_query_name", new_column_name="source_query")


def downgrade() -> None:
    op.alter_column("mapping_templates", "source_object", new_column_name="tririga_module")
    op.alter_column("mapping_templates", "source_query", new_column_name="tririga_query_name")
    # Note: PostgreSQL does not support removing enum values; downgrade only renames columns

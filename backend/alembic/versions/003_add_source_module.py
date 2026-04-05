"""Add source_module to mapping_templates

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column("source_module", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("mapping_templates", "source_module")

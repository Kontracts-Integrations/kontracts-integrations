"""add associated object fields to mapping_templates

Revision ID: 004
Revises: 003
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mapping_templates", sa.Column("fetch_associated", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("mapping_templates", sa.Column("assoc_module", sa.String(255), nullable=True))
    op.add_column("mapping_templates", sa.Column("assoc_object", sa.String(255), nullable=True))
    op.add_column("mapping_templates", sa.Column("assoc_string", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("mapping_templates", "assoc_string")
    op.drop_column("mapping_templates", "assoc_object")
    op.drop_column("mapping_templates", "assoc_module")
    op.drop_column("mapping_templates", "fetch_associated")

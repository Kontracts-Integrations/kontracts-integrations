"""add lookup key fields / indexed lookup keys

Adds mapping_templates.lookup_key_fields (JSONB list of source field names to
index as lookup keys) and lease_mappings.lookup_keys (JSONB list of the resolved
business-key values pointing to the produced kontracts_id), so a writing mapping
can expose extra keys that subsequent mappings resolve the target id by.

Revision ID: 010
Revises: 009
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column("lookup_key_fields", JSONB(), nullable=True),
    )
    op.add_column(
        "lease_mappings",
        sa.Column("lookup_keys", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lease_mappings", "lookup_keys")
    op.drop_column("mapping_templates", "lookup_key_fields")

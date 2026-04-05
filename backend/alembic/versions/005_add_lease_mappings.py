"""add lease_mappings table

Revision ID: 005
Revises: 004
Create Date: 2026-04-01
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lease_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tririga_lease_id", sa.String(255), nullable=False),
        sa.Column("tririga_record_id", sa.String(255), nullable=False),
        sa.Column("kontracts_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lease_mappings_tririga_lease_id", "lease_mappings", ["tririga_lease_id"])
    op.create_index("ix_lease_mappings_tririga_record_id", "lease_mappings", ["tririga_record_id"])
    op.create_index("ix_lease_mappings_kontracts_id", "lease_mappings", ["kontracts_id"])


def downgrade() -> None:
    op.drop_index("ix_lease_mappings_kontracts_id", "lease_mappings")
    op.drop_index("ix_lease_mappings_tririga_record_id", "lease_mappings")
    op.drop_index("ix_lease_mappings_tririga_lease_id", "lease_mappings")
    op.drop_table("lease_mappings")

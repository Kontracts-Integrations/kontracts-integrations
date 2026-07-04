"""add record_sync_state for upsert on subsequent runs

Adds the record_sync_state table (per-mapping, per-source-record kontracts_id +
payload hash) and an update_existing flag on mapping_templates.

Revision ID: 008
Revises: 007
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mapping_templates",
        sa.Column(
            "update_existing", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_table(
        "record_sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "mapping_template_id",
            sa.Integer(),
            sa.ForeignKey("mapping_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_record_id", sa.String(255), nullable=False),
        sa.Column("kontracts_id", sa.String(255), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "mapping_template_id",
            "source_record_id",
            name="uq_record_sync_template_record",
        ),
    )
    op.create_index(
        "ix_record_sync_state_mapping_template_id",
        "record_sync_state",
        ["mapping_template_id"],
    )
    op.create_index(
        "ix_record_sync_state_source_record_id",
        "record_sync_state",
        ["source_record_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_record_sync_state_source_record_id", "record_sync_state")
    op.drop_index("ix_record_sync_state_mapping_template_id", "record_sync_state")
    op.drop_table("record_sync_state")
    op.drop_column("mapping_templates", "update_existing")

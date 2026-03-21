"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # connections table
    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "connection_type",
            sa.Enum("tririga", "kontracts", name="connectiontype"),
            nullable=False,
        ),
        sa.Column("encrypted_credentials", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_connections_id"), "connections", ["id"], unique=False)

    # mapping_templates table
    op.create_table(
        "mapping_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "source_connection_id",
            sa.Integer(),
            sa.ForeignKey("connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "target_connection_id",
            sa.Integer(),
            sa.ForeignKey("connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tririga_module", sa.String(length=255), nullable=True),
        sa.Column("tririga_query_name", sa.String(length=255), nullable=True),
        sa.Column("kontracts_endpoint", sa.String(length=255), nullable=True),
        sa.Column("kontracts_method", sa.String(length=10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mapping_templates_id"), "mapping_templates", ["id"], unique=False
    )

    # mapping_versions table
    op.create_table(
        "mapping_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("mapping_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "field_mappings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mapping_versions_id"), "mapping_versions", ["id"], unique=False
    )

    # sync_runs table
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "mapping_template_id",
            sa.Integer(),
            sa.ForeignKey("mapping_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="runstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("triggered_by", sa.String(length=255), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sync_runs_id"), "sync_runs", ["id"], unique=False)

    # sync_records table
    op.create_table(
        "sync_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("sync_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tririga_record_id", sa.String(length=255), nullable=True),
        sa.Column("kontracts_record_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("success", "failed", "skipped", name="recordstatus"),
            nullable=False,
        ),
        sa.Column(
            "source_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "mapped_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sync_records_id"), "sync_records", ["id"], unique=False
    )

    # log_entries table
    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("sync_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "level",
            sa.Enum("debug", "info", "warning", "error", name="loglevel"),
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("component", sa.String(length=255), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_log_entries_id"), "log_entries", ["id"], unique=False
    )
    op.create_index(
        "ix_log_entries_created_at", "log_entries", ["created_at"], unique=False
    )
    op.create_index(
        "ix_log_entries_level", "log_entries", ["level"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_log_entries_level", table_name="log_entries")
    op.drop_index("ix_log_entries_created_at", table_name="log_entries")
    op.drop_index(op.f("ix_log_entries_id"), table_name="log_entries")
    op.drop_table("log_entries")
    op.drop_index(op.f("ix_sync_records_id"), table_name="sync_records")
    op.drop_table("sync_records")
    op.drop_index(op.f("ix_sync_runs_id"), table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index(op.f("ix_mapping_versions_id"), table_name="mapping_versions")
    op.drop_table("mapping_versions")
    op.drop_index(op.f("ix_mapping_templates_id"), table_name="mapping_templates")
    op.drop_table("mapping_templates")
    op.drop_index(op.f("ix_connections_id"), table_name="connections")
    op.drop_table("connections")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS connectiontype")
    op.execute("DROP TYPE IF EXISTS runstatus")
    op.execute("DROP TYPE IF EXISTS recordstatus")
    op.execute("DROP TYPE IF EXISTS loglevel")

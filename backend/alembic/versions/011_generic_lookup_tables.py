"""generic id-mapping table + named lookup-table registry

- Renames the physical table lease_mappings -> id_mappings (it is a generic
  source->target ID store, not tied to any particular mapping) and renames its
  TRIRIGA-specific columns to generic names.
- Migrates the default bucket name "lease_mappings" -> "default".
- Adds a lookup_tables registry so named lookup tables are discoverable by other
  mappings as soon as they are declared, and seeds it from existing usage.

Revision ID: 011
Revises: 010
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Rename the physical ID store to a generic name + generic columns.
    op.rename_table("lease_mappings", "id_mappings")
    op.alter_column("id_mappings", "tririga_lease_id", new_column_name="source_key")
    op.alter_column("id_mappings", "tririga_record_id", new_column_name="source_record_id")

    # 2. Migrate the default bucket name.
    op.execute(
        "UPDATE id_mappings SET table_name = 'default' WHERE table_name = 'lease_mappings'"
    )
    op.alter_column("id_mappings", "table_name", server_default="default")

    # 3. Named lookup-table registry.
    op.create_table(
        "lookup_tables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lookup_tables_id", "lookup_tables", ["id"])
    op.create_unique_constraint("uq_lookup_tables_name", "lookup_tables", ["name"])
    op.create_index("ix_lookup_tables_name", "lookup_tables", ["name"])

    # 4. Seed the registry from existing buckets + declared template names + default.
    op.execute("INSERT INTO lookup_tables (name) VALUES ('default') ON CONFLICT (name) DO NOTHING")
    op.execute(
        "INSERT INTO lookup_tables (name) "
        "SELECT DISTINCT table_name FROM id_mappings WHERE table_name IS NOT NULL "
        "ON CONFLICT (name) DO NOTHING"
    )
    op.execute(
        "INSERT INTO lookup_tables (name) "
        "SELECT DISTINCT lookup_table_name FROM mapping_templates "
        "WHERE lookup_table_name IS NOT NULL AND lookup_table_name <> '' "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("ix_lookup_tables_name", table_name="lookup_tables")
    op.drop_constraint("uq_lookup_tables_name", "lookup_tables", type_="unique")
    op.drop_index("ix_lookup_tables_id", table_name="lookup_tables")
    op.drop_table("lookup_tables")

    op.alter_column("id_mappings", "table_name", server_default="lease_mappings")
    op.execute(
        "UPDATE id_mappings SET table_name = 'lease_mappings' WHERE table_name = 'default'"
    )
    op.alter_column("id_mappings", "source_record_id", new_column_name="tririga_record_id")
    op.alter_column("id_mappings", "source_key", new_column_name="tririga_lease_id")
    op.rename_table("id_mappings", "lease_mappings")

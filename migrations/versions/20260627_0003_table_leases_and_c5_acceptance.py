from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0003"
down_revision = "20260627_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "table_leases",
        sa.Column("lease_id", sa.Text(), primary_key=True),
        sa.Column("table_ref_id", sa.Text(), nullable=False),
        sa.Column("lease_type", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("acquired_at", sa.Text(), nullable=False),
        sa.Column("last_heartbeat_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("released_at", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["table_ref_id"], ["data_refs.table_ref_id"]),
    )
    op.create_index("idx_table_leases_table_ref_id", "table_leases", ["table_ref_id"])
    op.create_index("idx_table_leases_lease_type", "table_leases", ["lease_type"])
    op.create_index("idx_table_leases_owner_id", "table_leases", ["owner_id"])
    op.create_index("idx_table_leases_status", "table_leases", ["status"])
    op.create_index("idx_table_leases_expires_at", "table_leases", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_table_leases_expires_at", table_name="table_leases")
    op.drop_index("idx_table_leases_status", table_name="table_leases")
    op.drop_index("idx_table_leases_owner_id", table_name="table_leases")
    op.drop_index("idx_table_leases_lease_type", table_name="table_leases")
    op.drop_index("idx_table_leases_table_ref_id", table_name="table_leases")
    op.drop_table("table_leases")

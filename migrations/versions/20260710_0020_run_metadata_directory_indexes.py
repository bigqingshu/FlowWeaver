from __future__ import annotations

from alembic import op

revision = "20260710_0020"
down_revision = "20260710_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_node_runs_run_status_directory",
        "node_runs",
        ["workflow_run_id", "status", "node_instance_id", "node_run_id"],
    )
    op.create_index(
        "idx_data_refs_run_directory",
        "data_refs",
        [
            "workflow_run_id",
            "lifecycle_status",
            "storage_kind",
            "role",
            "logical_table_id",
            "node_run_id",
            "created_at",
            "table_ref_id",
        ],
    )


def downgrade() -> None:
    op.drop_index("idx_data_refs_run_directory", table_name="data_refs")
    op.drop_index("idx_node_runs_run_status_directory", table_name="node_runs")

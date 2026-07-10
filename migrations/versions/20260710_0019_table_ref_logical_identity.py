from __future__ import annotations

from alembic import op

revision = "20260710_0019"
down_revision = "20260708_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("data_refs") as batch_op:
        batch_op.drop_constraint(
            "uq_data_refs_logical_version_run",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_data_refs_logical_identity_version",
            [
                "workflow_run_id",
                "storage_kind",
                "role",
                "logical_table_id",
                "version",
            ],
        )
        batch_op.create_index(
            "idx_data_refs_logical_identity_latest",
            [
                "workflow_run_id",
                "storage_kind",
                "role",
                "logical_table_id",
                "lifecycle_status",
                "version",
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("data_refs") as batch_op:
        batch_op.drop_index("idx_data_refs_logical_identity_latest")
        batch_op.drop_constraint(
            "uq_data_refs_logical_identity_version",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_data_refs_logical_version_run",
            ["logical_table_id", "version", "workflow_run_id"],
        )

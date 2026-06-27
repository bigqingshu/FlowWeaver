from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0002"
down_revision = "20260627_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("workflow_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("current_revision_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "workflow_revisions",
        sa.Column("revision_id", sa.Text(), primary_key=True),
        sa.Column("workflow_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition_json", sa.Text(), nullable=False),
        sa.Column("definition_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.workflow_id"]),
        sa.UniqueConstraint("workflow_id", "version"),
    )
    op.create_index(
        "idx_workflow_revisions_workflow_id",
        "workflow_revisions",
        ["workflow_id"],
    )

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("revision_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("definition_hash", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("state_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.create_index("idx_workflow_runs_revision_id", ["revision_id"])

    with op.batch_alter_table("node_runs") as batch_op:
        batch_op.add_column(
            sa.Column("state_version", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("data_refs") as batch_op:
        batch_op.add_column(sa.Column("resource_profile_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("mount_id", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("published_at", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("released_at", sa.Text(), nullable=True))
        batch_op.create_index("idx_data_refs_workflow_run_id", ["workflow_run_id"])
        batch_op.create_index("idx_data_refs_node_run_id", ["node_run_id"])
        batch_op.create_index("idx_data_refs_logical_table_id", ["logical_table_id"])
        batch_op.create_index("idx_data_refs_lifecycle_status", ["lifecycle_status"])
        batch_op.create_index("idx_data_refs_scope", ["scope"])
        batch_op.create_unique_constraint(
            "uq_data_refs_logical_version_run",
            ["logical_table_id", "version", "workflow_run_id"],
        )

    op.create_table(
        "runtime_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("event_version", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=True),
        sa.Column("node_run_id", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_runtime_events_sequence_number",
        "runtime_events",
        ["sequence_number"],
    )
    op.create_index(
        "idx_runtime_events_workflow_run_id",
        "runtime_events",
        ["workflow_run_id"],
    )
    op.create_index("idx_runtime_events_node_run_id", "runtime_events", ["node_run_id"])


def downgrade() -> None:
    op.drop_index("idx_runtime_events_node_run_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_workflow_run_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_sequence_number", table_name="runtime_events")
    op.drop_table("runtime_events")

    with op.batch_alter_table("data_refs") as batch_op:
        batch_op.drop_constraint("uq_data_refs_logical_version_run", type_="unique")
        batch_op.drop_index("idx_data_refs_scope")
        batch_op.drop_index("idx_data_refs_lifecycle_status")
        batch_op.drop_index("idx_data_refs_logical_table_id")
        batch_op.drop_index("idx_data_refs_node_run_id")
        batch_op.drop_index("idx_data_refs_workflow_run_id")
        batch_op.drop_column("released_at")
        batch_op.drop_column("published_at")
        batch_op.drop_column("mount_id")
        batch_op.drop_column("resource_profile_id")

    with op.batch_alter_table("node_runs") as batch_op:
        batch_op.drop_column("state_version")

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_index("idx_workflow_runs_revision_id")
        batch_op.drop_column("state_version")
        batch_op.drop_column("definition_hash")
        batch_op.drop_column("revision_id")

    op.drop_index("idx_workflow_revisions_workflow_id", table_name="workflow_revisions")
    op.drop_table("workflow_revisions")
    op.drop_table("workflows")

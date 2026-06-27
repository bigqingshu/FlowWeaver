from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("workflow_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("workflow_run_id", sa.Text(), primary_key=True),
        sa.Column("workflow_id", sa.Text(), nullable=False),
        sa.Column("workflow_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_snapshot_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow_definitions.workflow_id"]),
    )
    op.create_index("idx_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])
    op.create_index("idx_workflow_runs_status", "workflow_runs", ["status"])

    op.create_table(
        "node_runs",
        sa.Column("node_run_id", sa.Text(), primary_key=True),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("node_instance_id", sa.Text(), nullable=False),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("executor_id", sa.Text(), nullable=True),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("current_stage", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("last_heartbeat", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
    )

    op.create_table(
        "data_refs",
        sa.Column("table_ref_id", sa.Text(), primary_key=True),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("node_run_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("storage_kind", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("mutability", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("logical_table_id", sa.Text(), nullable=False),
        sa.Column("opaque_handle_json", sa.Text(), nullable=False),
        sa.Column("schema_json", sa.Text(), nullable=False),
        sa.Column("schema_fingerprint", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("capabilities_json", sa.Text(), nullable=False),
        sa.Column("lifecycle_status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "shared_publications",
        sa.Column("publication_id", sa.Text(), primary_key=True),
        sa.Column("share_name", sa.Text(), nullable=False),
        sa.Column("publication_version", sa.Integer(), nullable=False),
        sa.Column("producer_workflow_id", sa.Text(), nullable=False),
        sa.Column("producer_run_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_snapshot_id", sa.Text(), nullable=True),
        sa.Column("retention_policy_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("share_name", "publication_version"),
    )

    op.create_table(
        "shared_publication_members",
        sa.Column("publication_id", sa.Text(), nullable=False),
        sa.Column("export_name", sa.Text(), nullable=False),
        sa.Column("table_ref_id", sa.Text(), nullable=False),
        sa.Column("exact_table_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["publication_id"],
            ["shared_publications.publication_id"],
        ),
        sa.ForeignKeyConstraint(["table_ref_id"], ["data_refs.table_ref_id"]),
        sa.PrimaryKeyConstraint("publication_id", "export_name"),
    )

    op.create_table(
        "input_snapshots",
        sa.Column("input_snapshot_id", sa.Text(), primary_key=True),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )

    op.create_table(
        "read_leases",
        sa.Column("lease_id", sa.Text(), primary_key=True),
        sa.Column("publication_id", sa.Text(), nullable=False),
        sa.Column("publication_version", sa.Integer(), nullable=False),
        sa.Column("consumer_workflow_run_id", sa.Text(), nullable=False),
        sa.Column("selected_members_json", sa.Text(), nullable=False),
        sa.Column("acquired_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=False),
        sa.Column("released_at", sa.Text(), nullable=True),
    )

    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=True),
        sa.Column("node_run_id", sa.Text(), nullable=True),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("read_leases")
    op.drop_table("input_snapshots")
    op.drop_table("shared_publication_members")
    op.drop_table("shared_publications")
    op.drop_table("data_refs")
    op.drop_table("node_runs")
    op.drop_index("idx_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("idx_workflow_runs_workflow_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_definitions")

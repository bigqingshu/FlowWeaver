from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0007"
down_revision = "20260627_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_runtime_events_node_run_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_workflow_run_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_sequence_number", table_name="runtime_events")
    op.create_table(
        "runtime_events_new",
        sa.Column(
            "sequence_number",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("event_id", sa.Text(), nullable=False, unique=True),
        sa.Column("event_version", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=True),
        sa.Column("node_run_id", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sqlite_autoincrement=True,
    )
    op.execute(
        """
        INSERT INTO runtime_events_new (
            sequence_number,
            event_id,
            event_version,
            event_type,
            timestamp,
            workflow_run_id,
            node_run_id,
            payload_json
        )
        SELECT
            sequence_number,
            event_id,
            event_version,
            event_type,
            timestamp,
            workflow_run_id,
            node_run_id,
            payload_json
        FROM runtime_events
        ORDER BY sequence_number
        """
    )
    op.drop_table("runtime_events")
    op.rename_table("runtime_events_new", "runtime_events")
    op.create_index(
        "idx_runtime_events_workflow_run_id",
        "runtime_events",
        ["workflow_run_id"],
    )
    op.create_index("idx_runtime_events_node_run_id", "runtime_events", ["node_run_id"])


def downgrade() -> None:
    op.drop_index("idx_runtime_events_node_run_id", table_name="runtime_events")
    op.drop_index("idx_runtime_events_workflow_run_id", table_name="runtime_events")
    op.create_table(
        "runtime_events_old",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("event_version", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=True),
        sa.Column("node_run_id", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.execute(
        """
        INSERT INTO runtime_events_old (
            event_id,
            sequence_number,
            event_version,
            event_type,
            timestamp,
            workflow_run_id,
            node_run_id,
            payload_json
        )
        SELECT
            event_id,
            sequence_number,
            event_version,
            event_type,
            timestamp,
            workflow_run_id,
            node_run_id,
            payload_json
        FROM runtime_events
        ORDER BY sequence_number
        """
    )
    op.drop_table("runtime_events")
    op.rename_table("runtime_events_old", "runtime_events")
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

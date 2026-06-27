from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0004"
down_revision = "20260627_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_processes",
        sa.Column("process_id", sa.Text(), primary_key=True),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("os_pid", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("last_heartbeat_at", sa.Text(), nullable=True),
        sa.Column("cancel_requested_at", sa.Text(), nullable=True),
        sa.Column("exited_at", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
    )
    op.create_index(
        "idx_workflow_processes_workflow_run_id",
        "workflow_processes",
        ["workflow_run_id"],
    )
    op.create_index(
        "idx_workflow_processes_status",
        "workflow_processes",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("idx_workflow_processes_status", table_name="workflow_processes")
    op.drop_index(
        "idx_workflow_processes_workflow_run_id",
        table_name="workflow_processes",
    )
    op.drop_table("workflow_processes")

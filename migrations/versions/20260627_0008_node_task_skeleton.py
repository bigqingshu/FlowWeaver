from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0008"
down_revision = "20260627_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "node_tasks",
        sa.Column("task_id", sa.Text(), primary_key=True),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("workflow_process_id", sa.Text(), nullable=False),
        sa.Column("process_generation", sa.Integer(), nullable=False),
        sa.Column("node_run_id", sa.Text(), nullable=False),
        sa.Column("node_instance_id", sa.Text(), nullable=False),
        sa.Column("node_type", sa.Text(), nullable=False),
        sa.Column("node_version", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_refs_json", sa.Text(), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("permission_handle_id", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.workflow_run_id"]),
        sa.ForeignKeyConstraint(
            ["workflow_process_id"],
            ["workflow_processes.process_id"],
        ),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.node_run_id"]),
    )
    op.create_index("idx_node_tasks_workflow_run_id", "node_tasks", ["workflow_run_id"])
    op.create_index(
        "idx_node_tasks_workflow_process_id",
        "node_tasks",
        ["workflow_process_id"],
    )
    op.create_index("idx_node_tasks_node_run_id", "node_tasks", ["node_run_id"])

    op.create_table(
        "node_task_results",
        sa.Column("result_id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), nullable=False),
        sa.Column("node_run_id", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("executor_id", sa.Text(), nullable=False),
        sa.Column("process_generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("output_refs_json", sa.Text(), nullable=False),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("finished_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["node_tasks.task_id"]),
        sa.ForeignKeyConstraint(["node_run_id"], ["node_runs.node_run_id"]),
        sa.UniqueConstraint("task_id", "result_id"),
    )
    op.create_index("idx_node_task_results_task_id", "node_task_results", ["task_id"])
    op.create_index(
        "idx_node_task_results_node_run_id",
        "node_task_results",
        ["node_run_id"],
    )
    op.create_index(
        "idx_node_task_results_executor_id",
        "node_task_results",
        ["executor_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_node_task_results_executor_id", table_name="node_task_results")
    op.drop_index("idx_node_task_results_node_run_id", table_name="node_task_results")
    op.drop_index("idx_node_task_results_task_id", table_name="node_task_results")
    op.drop_table("node_task_results")
    op.drop_index("idx_node_tasks_node_run_id", table_name="node_tasks")
    op.drop_index("idx_node_tasks_workflow_process_id", table_name="node_tasks")
    op.drop_index("idx_node_tasks_workflow_run_id", table_name="node_tasks")
    op.drop_table("node_tasks")

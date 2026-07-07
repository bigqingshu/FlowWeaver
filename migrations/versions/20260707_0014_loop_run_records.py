from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260707_0014"
down_revision = "20260707_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loop_runs",
        sa.Column("loop_run_id", sa.Text(), primary_key=True),
        sa.Column(
            "workflow_run_id",
            sa.Text(),
            sa.ForeignKey("workflow_runs.workflow_run_id"),
            nullable=False,
        ),
        sa.Column("loop_id", sa.Text(), nullable=False),
        sa.Column("start_node_instance_id", sa.Text(), nullable=False),
        sa.Column("judge_node_instance_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "current_iteration",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("max_iterations", sa.Integer(), nullable=False),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("workflow_run_id", "loop_id"),
    )
    op.create_index("ix_loop_runs_workflow_run_id", "loop_runs", ["workflow_run_id"])
    op.create_index("ix_loop_runs_loop_id", "loop_runs", ["loop_id"])
    op.create_index("ix_loop_runs_status", "loop_runs", ["status"])
    op.create_index(
        "ix_loop_runs_workflow_status",
        "loop_runs",
        ["workflow_run_id", "status"],
    )

    op.create_table(
        "loop_iteration_runs",
        sa.Column("loop_iteration_id", sa.Text(), primary_key=True),
        sa.Column(
            "loop_run_id",
            sa.Text(),
            sa.ForeignKey("loop_runs.loop_run_id"),
            nullable=False,
        ),
        sa.Column("iteration_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "input_table_ref_id",
            sa.Text(),
            sa.ForeignKey("data_refs.table_ref_id"),
            nullable=True,
        ),
        sa.Column("input_selector_json", sa.Text(), nullable=True),
        sa.Column(
            "output_table_ref_id",
            sa.Text(),
            sa.ForeignKey("data_refs.table_ref_id"),
            nullable=True,
        ),
        sa.Column(
            "failed_node_run_id",
            sa.Text(),
            sa.ForeignKey("node_runs.node_run_id"),
            nullable=True,
        ),
        sa.Column("started_at", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("loop_run_id", "iteration_index"),
    )
    op.create_index(
        "ix_loop_iteration_runs_loop_run_id",
        "loop_iteration_runs",
        ["loop_run_id"],
    )
    op.create_index(
        "ix_loop_iteration_runs_status",
        "loop_iteration_runs",
        ["status"],
    )
    op.create_index(
        "ix_loop_iteration_runs_input_table_ref_id",
        "loop_iteration_runs",
        ["input_table_ref_id"],
    )
    op.create_index(
        "ix_loop_iteration_runs_output_table_ref_id",
        "loop_iteration_runs",
        ["output_table_ref_id"],
    )
    op.create_index(
        "ix_loop_iteration_runs_failed_node_run_id",
        "loop_iteration_runs",
        ["failed_node_run_id"],
    )
    op.create_index(
        "ix_loop_iteration_runs_loop_status",
        "loop_iteration_runs",
        ["loop_run_id", "status"],
    )

    op.create_table(
        "loop_iteration_table_refs",
        sa.Column(
            "loop_iteration_id",
            sa.Text(),
            sa.ForeignKey("loop_iteration_runs.loop_iteration_id"),
            primary_key=True,
        ),
        sa.Column(
            "table_ref_id",
            sa.Text(),
            sa.ForeignKey("data_refs.table_ref_id"),
            primary_key=True,
        ),
        sa.Column("role", sa.Text(), primary_key=True),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_loop_iteration_table_refs_iteration_role",
        "loop_iteration_table_refs",
        ["loop_iteration_id", "role"],
    )
    op.create_index(
        "ix_loop_iteration_table_refs_table_ref_id",
        "loop_iteration_table_refs",
        ["table_ref_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_loop_iteration_table_refs_table_ref_id",
        table_name="loop_iteration_table_refs",
    )
    op.drop_index(
        "ix_loop_iteration_table_refs_iteration_role",
        table_name="loop_iteration_table_refs",
    )
    op.drop_table("loop_iteration_table_refs")

    op.drop_index(
        "ix_loop_iteration_runs_loop_status",
        table_name="loop_iteration_runs",
    )
    op.drop_index(
        "ix_loop_iteration_runs_failed_node_run_id",
        table_name="loop_iteration_runs",
    )
    op.drop_index(
        "ix_loop_iteration_runs_output_table_ref_id",
        table_name="loop_iteration_runs",
    )
    op.drop_index(
        "ix_loop_iteration_runs_input_table_ref_id",
        table_name="loop_iteration_runs",
    )
    op.drop_index("ix_loop_iteration_runs_status", table_name="loop_iteration_runs")
    op.drop_index(
        "ix_loop_iteration_runs_loop_run_id",
        table_name="loop_iteration_runs",
    )
    op.drop_table("loop_iteration_runs")

    op.drop_index("ix_loop_runs_workflow_status", table_name="loop_runs")
    op.drop_index("ix_loop_runs_status", table_name="loop_runs")
    op.drop_index("ix_loop_runs_loop_id", table_name="loop_runs")
    op.drop_index("ix_loop_runs_workflow_run_id", table_name="loop_runs")
    op.drop_table("loop_runs")

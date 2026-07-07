from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260708_0015"
down_revision = "20260707_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loop_iteration_node_runs",
        sa.Column(
            "loop_iteration_id",
            sa.Text(),
            sa.ForeignKey("loop_iteration_runs.loop_iteration_id"),
            primary_key=True,
        ),
        sa.Column(
            "node_run_id",
            sa.Text(),
            sa.ForeignKey("node_runs.node_run_id"),
            primary_key=True,
        ),
        sa.Column("node_instance_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_loop_iteration_node_runs_iteration_instance",
        "loop_iteration_node_runs",
        ["loop_iteration_id", "node_instance_id"],
    )
    op.create_index(
        "ix_loop_iteration_node_runs_node_run_id",
        "loop_iteration_node_runs",
        ["node_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_loop_iteration_node_runs_node_run_id",
        table_name="loop_iteration_node_runs",
    )
    op.drop_index(
        "ix_loop_iteration_node_runs_iteration_instance",
        table_name="loop_iteration_node_runs",
    )
    op.drop_table("loop_iteration_node_runs")

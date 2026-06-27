from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260627_0006"
down_revision = "20260627_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("owner_process_id", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "process_generation",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("fencing_token", sa.Text(), nullable=True))
        batch_op.create_index(
            "idx_workflow_runs_owner_process_id",
            ["owner_process_id"],
        )

    with op.batch_alter_table("workflow_processes") as batch_op:
        batch_op.add_column(
            sa.Column(
                "process_generation",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(sa.Column("fencing_token", sa.Text(), nullable=True))
    op.create_index(
        "uq_workflow_processes_active_run",
        "workflow_processes",
        ["workflow_run_id"],
        unique=True,
        sqlite_where=sa.text(
            "status IN ('STARTING', 'RUNNING', 'CANCEL_REQUESTED')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_workflow_processes_active_run",
        table_name="workflow_processes",
    )
    with op.batch_alter_table("workflow_processes") as batch_op:
        batch_op.drop_column("fencing_token")
        batch_op.drop_column("process_generation")

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_index("idx_workflow_runs_owner_process_id")
        batch_op.drop_column("fencing_token")
        batch_op.drop_column("process_generation")
        batch_op.drop_column("owner_process_id")

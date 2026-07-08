from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260708_0017"
down_revision = "20260708_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "trigger_source",
                sa.Text(),
                nullable=False,
                server_default="manual",
            )
        )
    op.create_index(
        "ix_workflow_runs_trigger_source",
        "workflow_runs",
        ["trigger_source"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_runs_trigger_source",
        table_name="workflow_runs",
    )
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("trigger_source")

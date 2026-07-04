from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260704_0011"
down_revision = "20260629_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "run_mode",
                sa.Text(),
                nullable=False,
                server_default="full",
            )
        )
        batch_op.add_column(
            sa.Column(
                "target_node_instance_id",
                sa.Text(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("target_node_instance_id")
        batch_op.drop_column("run_mode")

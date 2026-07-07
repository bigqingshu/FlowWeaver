from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260707_0013"
down_revision = "20260705_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_task_results") as batch_op:
        batch_op.add_column(
            sa.Column(
                "summary_json",
                sa.Text(),
                nullable=False,
                server_default="{}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("node_task_results") as batch_op:
        batch_op.drop_column("summary_json")

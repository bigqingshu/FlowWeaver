from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260708_0018"
down_revision = "20260708_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_task_results") as batch_op:
        batch_op.add_column(
            sa.Column(
                "output_slot_bindings_json",
                sa.Text(),
                nullable=False,
                server_default="{}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("node_task_results") as batch_op:
        batch_op.drop_column("output_slot_bindings_json")

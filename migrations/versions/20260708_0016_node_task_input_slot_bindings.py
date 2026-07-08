from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260708_0016"
down_revision = "20260708_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "input_slot_bindings_json",
                sa.Text(),
                nullable=False,
                server_default="{}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.drop_column("input_slot_bindings_json")

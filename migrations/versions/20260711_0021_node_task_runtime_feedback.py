from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_0021"
down_revision = "20260710_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "runtime_feedback_policy_json",
                sa.Text(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "runtime_options_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.drop_column("runtime_options_version")
        batch_op.drop_column("runtime_feedback_policy_json")

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260628_0009"
down_revision = "20260627_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("completion_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("completion_reason")

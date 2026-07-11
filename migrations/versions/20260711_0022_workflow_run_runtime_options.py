from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_0022"
down_revision = "20260711_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_run_runtime_options",
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("requested_version", sa.Integer(), nullable=False),
        sa.Column("applied_version", sa.Integer(), nullable=False),
        sa.Column("overlay_json", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.Text(), nullable=False),
        sa.Column("applied_at", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "requested_version >= 0",
            name="ck_workflow_run_runtime_options_requested_version",
        ),
        sa.CheckConstraint(
            "applied_version >= 0 AND applied_version <= requested_version",
            name="ck_workflow_run_runtime_options_applied_version",
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["workflow_runs.workflow_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workflow_run_id"),
    )


def downgrade() -> None:
    op.drop_table("workflow_run_runtime_options")

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260705_0012"
down_revision = "20260704_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.drop_column("permission_handle_id")
    op.drop_table("permission_grants")
    op.drop_table("audit_events")


def downgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.Text(), primary_key=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=True),
        sa.Column("node_run_id", sa.Text(), nullable=True),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("audit_level", sa.Text(), nullable=False, server_default="STANDARD"),
        sa.Column("summary_json", sa.Text(), nullable=False),
    )
    with op.batch_alter_table("node_tasks") as batch_op:
        batch_op.add_column(sa.Column("permission_handle_id", sa.Text(), nullable=True))
    op.create_table(
        "permission_grants",
        sa.Column("permission_handle_id", sa.Text(), primary_key=True),
        sa.Column("request_id", sa.Text(), nullable=False),
        sa.Column("workflow_run_id", sa.Text(), nullable=False),
        sa.Column("node_run_id", sa.Text(), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("issued_at", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.Text(), nullable=True),
        sa.Column("denial_reason", sa.Text(), nullable=True),
        sa.Column("audit_level", sa.Text(), nullable=False),
    )
    op.create_index(
        "ix_permission_grants_request_id",
        "permission_grants",
        ["request_id"],
    )
    op.create_index(
        "ix_permission_grants_workflow_run_id",
        "permission_grants",
        ["workflow_run_id"],
    )
    op.create_index(
        "ix_permission_grants_node_run_id",
        "permission_grants",
        ["node_run_id"],
    )
    op.create_index(
        "ix_permission_grants_granted",
        "permission_grants",
        ["granted"],
    )

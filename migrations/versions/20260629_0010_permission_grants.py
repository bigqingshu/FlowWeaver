from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260629_0010"
down_revision = "20260628_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.add_column(
            sa.Column(
                "audit_level",
                sa.Text(),
                nullable=False,
                server_default="STANDARD",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.drop_column("audit_level")
    op.drop_index("ix_permission_grants_granted", table_name="permission_grants")
    op.drop_index("ix_permission_grants_node_run_id", table_name="permission_grants")
    op.drop_index(
        "ix_permission_grants_workflow_run_id",
        table_name="permission_grants",
    )
    op.drop_index("ix_permission_grants_request_id", table_name="permission_grants")
    op.drop_table("permission_grants")

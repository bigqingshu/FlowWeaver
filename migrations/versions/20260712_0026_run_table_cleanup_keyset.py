from __future__ import annotations

from alembic import op

revision = "20260712_0026"
down_revision = "20260712_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_data_refs_run_cleanup_keyset",
        "data_refs",
        ["workflow_run_id", "created_at", "table_ref_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_data_refs_run_cleanup_keyset",
        table_name="data_refs",
    )

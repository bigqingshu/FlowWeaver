from __future__ import annotations

from alembic import op

revision = "20260711_0023"
down_revision = "20260711_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_shared_publications_catalog",
        "shared_publications",
        ["share_name", "status", "publication_version"],
    )
    op.create_index(
        "idx_shared_publication_members_publication_export",
        "shared_publication_members",
        ["publication_id", "export_name"],
    )
    op.create_index(
        "idx_shared_publication_members_table_ref",
        "shared_publication_members",
        ["table_ref_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_shared_publication_members_table_ref",
        table_name="shared_publication_members",
    )
    op.drop_index(
        "idx_shared_publication_members_publication_export",
        table_name="shared_publication_members",
    )
    op.drop_index(
        "idx_shared_publications_catalog",
        table_name="shared_publications",
    )

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20260711_0024"
down_revision = "20260711_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shared_publications",
        sa.Column("expires_at", sa.Text(), nullable=True),
    )
    op.add_column(
        "shared_publications",
        sa.Column("release_started_at", sa.Text(), nullable=True),
    )
    op.add_column(
        "shared_publications",
        sa.Column("cleanup_last_progress_at", sa.Text(), nullable=True),
    )
    op.add_column(
        "shared_publications",
        sa.Column("released_at", sa.Text(), nullable=True),
    )
    op.add_column(
        "shared_publications",
        sa.Column(
            "cleanup_attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "shared_publications",
        sa.Column("last_cleanup_error_json", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_shared_publications_status_expires",
        "shared_publications",
        ["status", "expires_at"],
    )
    op.create_index(
        "idx_shared_publications_status_cleanup_progress",
        "shared_publications",
        ["status", "cleanup_last_progress_at"],
    )
    op.create_index(
        "idx_shared_publications_status_catalog",
        "shared_publications",
        ["status", "share_name", "publication_version"],
    )
    op.create_index(
        "idx_read_leases_publication_blocker",
        "read_leases",
        ["publication_id", "released_at", "expires_at"],
    )
    _backfill_expires_at()


def downgrade() -> None:
    op.drop_index(
        "idx_read_leases_publication_blocker",
        table_name="read_leases",
    )
    op.drop_index(
        "idx_shared_publications_status_catalog",
        table_name="shared_publications",
    )
    op.drop_index(
        "idx_shared_publications_status_cleanup_progress",
        table_name="shared_publications",
    )
    op.drop_index(
        "idx_shared_publications_status_expires",
        table_name="shared_publications",
    )
    op.drop_column("shared_publications", "last_cleanup_error_json")
    op.drop_column("shared_publications", "cleanup_attempt_count")
    op.drop_column("shared_publications", "released_at")
    op.drop_column("shared_publications", "cleanup_last_progress_at")
    op.drop_column("shared_publications", "release_started_at")
    op.drop_column("shared_publications", "expires_at")


def _backfill_expires_at() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT publication_id, retention_policy_json, created_at "
            "FROM shared_publications"
        )
    ).mappings()
    for row in rows:
        expires_at = _legacy_expires_at(
            retention_policy_json=row["retention_policy_json"],
            created_at=row["created_at"],
        )
        if expires_at is None:
            continue
        connection.execute(
            sa.text(
                "UPDATE shared_publications "
                "SET expires_at = :expires_at "
                "WHERE publication_id = :publication_id"
            ),
            {
                "publication_id": row["publication_id"],
                "expires_at": expires_at,
            },
        )


def _legacy_expires_at(
    *,
    retention_policy_json: Any,
    created_at: Any,
) -> str | None:
    try:
        retention_policy = json.loads(str(retention_policy_json))
        retention_seconds = retention_policy.get("retention_seconds")
        if (
            isinstance(retention_seconds, bool)
            or not isinstance(retention_seconds, int)
            or retention_seconds <= 0
        ):
            return None
        created = datetime.fromisoformat(str(created_at))
        return (created + timedelta(seconds=retention_seconds)).isoformat()
    except (
        AttributeError,
        OverflowError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None

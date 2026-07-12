from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class SharedPublicationRecord(Base):
    __tablename__ = "shared_publications"
    __table_args__ = (
        UniqueConstraint("share_name", "publication_version"),
        Index(
            "idx_shared_publications_catalog",
            "share_name",
            "status",
            "publication_version",
        ),
        Index(
            "idx_shared_publications_status_expires",
            "status",
            "expires_at",
        ),
        Index(
            "idx_shared_publications_status_cleanup_progress",
            "status",
            "cleanup_last_progress_at",
        ),
        Index(
            "idx_shared_publications_status_catalog",
            "status",
            "share_name",
            "publication_version",
        ),
    )

    publication_id: Mapped[str] = mapped_column(Text, primary_key=True)
    share_name: Mapped[str] = mapped_column(Text, nullable=False)
    publication_version: Mapped[int] = mapped_column(Integer, nullable=False)
    producer_workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    producer_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot_id: Mapped[str | None] = mapped_column(Text)
    retention_policy_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str | None] = mapped_column(Text)
    release_started_at: Mapped[str | None] = mapped_column(Text)
    cleanup_last_progress_at: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[str | None] = mapped_column(Text)
    cleanup_attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_cleanup_error_json: Mapped[str | None] = mapped_column(Text)


class SharedPublicationMemberRecord(Base):
    __tablename__ = "shared_publication_members"
    __table_args__ = (
        Index(
            "idx_shared_publication_members_publication_export",
            "publication_id",
            "export_name",
        ),
        Index(
            "idx_shared_publication_members_table_ref",
            "table_ref_id",
        ),
    )

    publication_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("shared_publications.publication_id"),
        primary_key=True,
    )
    export_name: Mapped[str] = mapped_column(Text, primary_key=True)
    table_ref_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        nullable=False,
    )
    exact_table_version: Mapped[int] = mapped_column(Integer, nullable=False)


class InputSnapshotRecord(Base):
    __tablename__ = "input_snapshots"

    input_snapshot_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)


class ReadLeaseRecord(Base):
    __tablename__ = "read_leases"
    __table_args__ = (
        Index(
            "idx_read_leases_publication_blocker",
            "publication_id",
            "released_at",
            "expires_at",
        ),
    )

    lease_id: Mapped[str] = mapped_column(Text, primary_key=True)
    publication_id: Mapped[str] = mapped_column(Text, nullable=False)
    publication_version: Mapped[int] = mapped_column(Integer, nullable=False)
    consumer_workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    selected_members_json: Mapped[str] = mapped_column(Text, nullable=False)
    acquired_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False)
    released_at: Mapped[str | None] = mapped_column(Text)

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from flowweaver.engine.db_base import Base


class DataRefRecord(Base):
    __tablename__ = "data_refs"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "storage_kind",
            "role",
            "logical_table_id",
            "version",
            name="uq_data_refs_logical_identity_version",
        ),
        Index(
            "idx_data_refs_logical_identity_latest",
            "workflow_run_id",
            "storage_kind",
            "role",
            "logical_table_id",
            "lifecycle_status",
            "version",
        ),
    )

    table_ref_id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    node_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    storage_kind: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    mutability: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)
    resource_profile_id: Mapped[str | None] = mapped_column(Text)
    mount_id: Mapped[str | None] = mapped_column(Text)
    logical_table_id: Mapped[str] = mapped_column(Text, nullable=False)
    opaque_handle_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    schema_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    capabilities_json: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[str | None] = mapped_column(Text)


class TableLeaseRecord(Base):
    __tablename__ = "table_leases"

    lease_id: Mapped[str] = mapped_column(Text, primary_key=True)
    table_ref_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("data_refs.table_ref_id"),
        nullable=False,
        index=True,
    )
    lease_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    acquired_at: Mapped[str] = mapped_column(Text, nullable=False)
    last_heartbeat_at: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    released_at: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False)

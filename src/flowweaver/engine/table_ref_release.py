from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy import select

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    TableLeaseRecord,
)
from flowweaver.engine.immediate_session import immediate_session
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _table_ref_from_record,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.table_provider_registry import TableProviderRegistry
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableLeaseStatus,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import TableRefModel


class TableRefReleaseOutcome(str, Enum):
    RELEASED = "RELEASED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class TableRefReleaseResult:
    table_ref_id: str
    outcome: TableRefReleaseOutcome
    table_ref: TableRefModel | None = None
    reason: str | None = None


@dataclass(frozen=True)
class _TableRefReleaseClaim:
    table_ref: TableRefModel | None
    reason: str | None = None


_INTERNAL_RELEASE_STORAGE_KINDS = {
    TableStorageKind.RUNTIME_SQL,
    TableStorageKind.MEMORY,
}
_UNAVAILABLE_LIFECYCLE_STATUSES = {
    LifecycleStatus.RELEASED.value,
    LifecycleStatus.RETIRED.value,
    LifecycleStatus.ORPHANED.value,
}
_ACTIVE_SHARED_PUBLICATION_STATUSES = {"PUBLISHED", "RELEASING"}


class TableRefReleaseService:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        provider_registry: TableProviderRegistry,
    ) -> None:
        self._store = store
        self._provider_registry = provider_registry

    def release(self, table_ref_id: str) -> TableRefReleaseResult:
        current = self._store.get_table_ref(table_ref_id)
        if current is None:
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.SKIPPED,
                reason="table_ref_not_found",
            )
        if current.storage_kind not in _INTERNAL_RELEASE_STORAGE_KINDS:
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.SKIPPED,
                table_ref=current,
                reason="external_or_unsupported_storage",
            )
        provider = self._provider_registry.get(current.provider_id)
        if provider is None or not self._provider_registry.supports_storage_kind(
            current.provider_id,
            current.storage_kind,
        ):
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.SKIPPED,
                table_ref=current,
                reason="provider_unsupported",
            )

        claim = self._claim(table_ref_id)
        if claim.table_ref is None:
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.SKIPPED,
                reason=claim.reason,
            )

        try:
            provider.drop_table(claim.table_ref)
        except Exception as exc:
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.FAILED,
                table_ref=claim.table_ref,
                reason=str(exc),
            )

        released = self._finalize(table_ref_id)
        if released is None:
            return TableRefReleaseResult(
                table_ref_id=table_ref_id,
                outcome=TableRefReleaseOutcome.FAILED,
                table_ref=self._store.get_table_ref(table_ref_id),
                reason="release_finalize_rejected",
            )
        return TableRefReleaseResult(
            table_ref_id=table_ref_id,
            outcome=TableRefReleaseOutcome.RELEASED,
            table_ref=released,
        )

    def _claim(self, table_ref_id: str) -> _TableRefReleaseClaim:
        now = utc_now()
        with immediate_session(self._store.engine) as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None:
                return _TableRefReleaseClaim(None, "table_ref_not_found")
            if record.lifecycle_status in _UNAVAILABLE_LIFECYCLE_STATUSES:
                return _TableRefReleaseClaim(None, "already_unavailable")
            if record.lifecycle_status == LifecycleStatus.RELEASABLE.value:
                return _TableRefReleaseClaim(_table_ref_from_record(record))
            if record.lifecycle_status != LifecycleStatus.PUBLISHED.value:
                return _TableRefReleaseClaim(
                    None,
                    f"lifecycle_status_{record.lifecycle_status.lower()}",
                )
            active_publication_id = session.scalar(
                select(SharedPublicationMemberRecord.publication_id)
                .join(
                    SharedPublicationRecord,
                    SharedPublicationRecord.publication_id
                    == SharedPublicationMemberRecord.publication_id,
                )
                .where(SharedPublicationMemberRecord.table_ref_id == table_ref_id)
                .where(
                    SharedPublicationRecord.status.in_(
                        _ACTIVE_SHARED_PUBLICATION_STATUSES
                    )
                )
                .limit(1)
            )
            if active_publication_id is not None:
                return _TableRefReleaseClaim(None, "shared_publication_active")
            active_table_lease_id = session.scalar(
                select(TableLeaseRecord.lease_id)
                .where(TableLeaseRecord.table_ref_id == table_ref_id)
                .where(TableLeaseRecord.status == TableLeaseStatus.ACTIVE.value)
                .where(TableLeaseRecord.expires_at > _datetime_to_text(now))
                .limit(1)
            )
            if active_table_lease_id is not None:
                return _TableRefReleaseClaim(None, "active_table_lease")
            record.lifecycle_status = LifecycleStatus.RELEASABLE.value
            return _TableRefReleaseClaim(_table_ref_from_record(record))

    def _finalize(self, table_ref_id: str) -> TableRefModel | None:
        now = utc_now()
        with immediate_session(self._store.engine) as session:
            record = session.get(DataRefRecord, table_ref_id)
            if record is None:
                return None
            if record.lifecycle_status == LifecycleStatus.RELEASED.value:
                return _table_ref_from_record(record)
            if record.lifecycle_status != LifecycleStatus.RELEASABLE.value:
                return None
            record.lifecycle_status = LifecycleStatus.RELEASED.value
            record.released_at = _datetime_to_text(now)
            return _table_ref_from_record(record)

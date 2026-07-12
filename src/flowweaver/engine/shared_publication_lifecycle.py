from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from flowweaver.common.time import utc_now
from flowweaver.engine.db_models import (
    DataRefRecord,
    ReadLeaseRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
    TableLeaseRecord,
    WorkflowRunRecord,
)
from flowweaver.engine.immediate_session import run_immediate_transaction
from flowweaver.engine.runtime_record_mappers import (
    _datetime_to_text,
    _json_dumps,
    _optional_datetime_from_text,
)
from flowweaver.engine.runtime_status_guards import TERMINAL_WORKFLOW_STATUS_VALUES
from flowweaver.engine.table_ref_release import (
    TableRefReleaseOutcome,
    TableRefReleaseResult,
    TableRefReleaseService,
)
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableLeaseStatus,
    TableMutability,
    TableStorageKind,
)

if TYPE_CHECKING:
    from flowweaver.engine.runtime_store import RuntimeStore


class SharedPublicationCleanupBlocker(str, Enum):
    PUBLICATION_NOT_PUBLISHED = "PUBLICATION_NOT_PUBLISHED"
    RETENTION_NOT_CONFIGURED = "RETENTION_NOT_CONFIGURED"
    RETENTION_NOT_EXPIRED = "RETENTION_NOT_EXPIRED"
    LATEST_VERSION_PROTECTED = "LATEST_VERSION_PROTECTED"
    PRODUCER_RUN_ACTIVE = "PRODUCER_RUN_ACTIVE"
    ACTIVE_READ_LEASE = "ACTIVE_READ_LEASE"
    ACTIVE_TABLE_LEASE = "ACTIVE_TABLE_LEASE"
    MEMBER_REFERENCED_BY_OTHER_PUBLICATION = (
        "MEMBER_REFERENCED_BY_OTHER_PUBLICATION"
    )
    MEMBER_NOT_RELEASABLE = "MEMBER_NOT_RELEASABLE"
    PUBLICATION_INCONSISTENT = "PUBLICATION_INCONSISTENT"


@dataclass(frozen=True)
class SharedPublicationCleanupPreview:
    publication_id: str
    eligible: bool
    status: str
    expires_at: datetime | None
    is_latest_published: bool
    active_read_lease_count: int
    active_table_lease_count: int
    releasable_member_count: int
    protected_member_count: int
    blockers: tuple[SharedPublicationCleanupBlocker, ...]


@dataclass(frozen=True)
class SharedPublicationCleanupClaimResult:
    publication_id: str
    claimed: bool
    preview: SharedPublicationCleanupPreview | None


class SharedPublicationCleanupOutcome(str, Enum):
    CLEANED = "CLEANED"
    ALREADY_RELEASED = "ALREADY_RELEASED"
    BLOCKED = "BLOCKED"
    RETRY_PENDING = "RETRY_PENDING"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class SharedPublicationCleanupMemberResult:
    table_ref_id: str
    outcome: str
    reason: str | None


@dataclass(frozen=True)
class SharedPublicationCleanupResult:
    publication_id: str
    outcome: SharedPublicationCleanupOutcome
    status: str | None
    processed_member_count: int = 0
    released_member_count: int = 0
    skipped_member_count: int = 0
    failed_member_count: int = 0
    remaining_member_count: int = 0
    blockers: tuple[SharedPublicationCleanupBlocker, ...] = ()
    member_results: tuple[SharedPublicationCleanupMemberResult, ...] = ()


@dataclass(frozen=True)
class _SharedPublicationCleanupPreparation:
    outcome: SharedPublicationCleanupOutcome | None
    status: str | None
    preview: SharedPublicationCleanupPreview | None


def calculate_shared_publication_expires_at(
    *,
    created_at: datetime,
    retention_policy: dict[str, object],
) -> datetime | None:
    retention_seconds = retention_policy.get("retention_seconds")
    if (
        isinstance(retention_seconds, bool)
        or not isinstance(retention_seconds, int)
        or retention_seconds <= 0
    ):
        return None
    try:
        return created_at + timedelta(seconds=retention_seconds)
    except OverflowError:
        return None


class SharedPublicationLifecycleService:
    def __init__(
        self,
        store: RuntimeStore,
        *,
        table_ref_release_service: TableRefReleaseService | None = None,
    ) -> None:
        self._store = store
        self._table_ref_release_service = table_ref_release_service

    def preview(
        self,
        publication_id: str,
        *,
        now: datetime | None = None,
    ) -> SharedPublicationCleanupPreview | None:
        evaluated_at = now or utc_now()
        with Session(self._store.engine) as session:
            evaluated = _evaluate_cleanup_from_session(
                session,
                publication_id=publication_id,
                now=evaluated_at,
            )
            return evaluated[1] if evaluated is not None else None

    def claim(
        self,
        publication_id: str,
        *,
        now: datetime | None = None,
    ) -> SharedPublicationCleanupClaimResult:
        claimed_at = now or utc_now()

        def operation(session: Session) -> SharedPublicationCleanupClaimResult:
            evaluated = _evaluate_cleanup_from_session(
                session,
                publication_id=publication_id,
                now=claimed_at,
            )
            if evaluated is None:
                return SharedPublicationCleanupClaimResult(
                    publication_id=publication_id,
                    claimed=False,
                    preview=None,
                )
            publication, preview = evaluated
            if not preview.eligible:
                return SharedPublicationCleanupClaimResult(
                    publication_id=publication_id,
                    claimed=False,
                    preview=preview,
                )
            timestamp = _datetime_to_text(claimed_at)
            publication.status = "RELEASING"
            publication.release_started_at = timestamp
            publication.cleanup_last_progress_at = timestamp
            publication.cleanup_attempt_count += 1
            publication.last_cleanup_error_json = None
            session.flush()
            return SharedPublicationCleanupClaimResult(
                publication_id=publication_id,
                claimed=True,
                preview=preview,
            )

        return run_immediate_transaction(self._store.engine, operation)

    def cleanup(
        self,
        publication_id: str,
        *,
        max_table_refs: int = 50,
        time_budget_seconds: float = 2.0,
        now: datetime | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> SharedPublicationCleanupResult:
        if self._table_ref_release_service is None:
            raise RuntimeError("TableRefReleaseService is required for cleanup")
        if not 1 <= max_table_refs <= 1000:
            raise ValueError("max_table_refs must be between 1 and 1000")
        if time_budget_seconds <= 0:
            raise ValueError("time_budget_seconds must be positive")
        if should_stop is not None and should_stop():
            return _interrupted_cleanup_result(publication_id, (), status=None)
        cleanup_started_at = now or utc_now()
        preparation = run_immediate_transaction(
            self._store.engine,
            lambda session: _prepare_cleanup_from_session(
                session,
                publication_id=publication_id,
                now=cleanup_started_at,
            ),
        )
        if preparation.outcome is not None:
            blockers = (
                preparation.preview.blockers
                if preparation.preview is not None
                else ()
            )
            return SharedPublicationCleanupResult(
                publication_id=publication_id,
                outcome=preparation.outcome,
                status=preparation.status,
                blockers=blockers,
            )

        candidate_ids = _list_actionable_table_ref_ids(
            self._store,
            publication_id=publication_id,
            limit=max_table_refs + 1,
        )
        if should_stop is not None and should_stop():
            return _interrupted_cleanup_result(publication_id, ())
        started = perf_counter()
        member_results: list[SharedPublicationCleanupMemberResult] = []
        retry_reasons: list[dict[str, str]] = []
        for table_ref_id in candidate_ids[:max_table_refs]:
            if should_stop is not None and should_stop():
                return _interrupted_cleanup_result(
                    publication_id,
                    tuple(member_results),
                )
            if perf_counter() - started >= time_budget_seconds:
                break
            release_result = self._table_ref_release_service.release(
                table_ref_id,
                excluding_publication_id=publication_id,
                should_stop=should_stop,
            )
            member_results.append(_cleanup_member_result(release_result))
            if _release_result_requires_retry(release_result):
                retry_reasons.append(
                    {
                        "table_ref_id": table_ref_id,
                        "reason": release_result.reason or "release_incomplete",
                    }
                )
            if should_stop is not None and should_stop():
                return _interrupted_cleanup_result(
                    publication_id,
                    tuple(member_results),
                )

        if should_stop is not None and should_stop():
            return _interrupted_cleanup_result(
                publication_id,
                tuple(member_results),
            )

        finalized, remaining_member_count = run_immediate_transaction(
            self._store.engine,
            lambda session: _finalize_or_record_cleanup_progress_from_session(
                session,
                publication_id=publication_id,
                now=now or utc_now(),
                retry_reasons=retry_reasons,
                max_remaining_count=max_table_refs + 1,
            ),
        )
        released_count = sum(
            result.outcome == TableRefReleaseOutcome.RELEASED.value
            for result in member_results
        )
        failed_count = sum(
            result.outcome == TableRefReleaseOutcome.FAILED.value
            for result in member_results
        )
        skipped_count = sum(
            result.outcome == TableRefReleaseOutcome.SKIPPED.value
            for result in member_results
        )
        return SharedPublicationCleanupResult(
            publication_id=publication_id,
            outcome=(
                SharedPublicationCleanupOutcome.CLEANED
                if finalized
                else SharedPublicationCleanupOutcome.RETRY_PENDING
            ),
            status="RELEASED" if finalized else "RELEASING",
            processed_member_count=len(member_results),
            released_member_count=released_count,
            skipped_member_count=skipped_count,
            failed_member_count=failed_count,
            remaining_member_count=remaining_member_count,
            member_results=tuple(member_results),
        )


def _prepare_cleanup_from_session(
    session: Session,
    *,
    publication_id: str,
    now: datetime,
) -> _SharedPublicationCleanupPreparation:
    publication = session.get(SharedPublicationRecord, publication_id)
    if publication is None:
        return _SharedPublicationCleanupPreparation(
            outcome=SharedPublicationCleanupOutcome.NOT_FOUND,
            status=None,
            preview=None,
        )
    if publication.status == "RELEASED":
        return _SharedPublicationCleanupPreparation(
            outcome=SharedPublicationCleanupOutcome.ALREADY_RELEASED,
            status=publication.status,
            preview=None,
        )
    if publication.status == "PUBLISHED":
        evaluated = _evaluate_cleanup_from_session(
            session,
            publication_id=publication_id,
            now=now,
        )
        if evaluated is None:
            return _SharedPublicationCleanupPreparation(
                outcome=SharedPublicationCleanupOutcome.NOT_FOUND,
                status=None,
                preview=None,
            )
        publication, preview = evaluated
        if not preview.eligible:
            return _SharedPublicationCleanupPreparation(
                outcome=SharedPublicationCleanupOutcome.BLOCKED,
                status=publication.status,
                preview=preview,
            )
        timestamp = _datetime_to_text(now)
        publication.status = "RELEASING"
        publication.release_started_at = timestamp
        publication.cleanup_last_progress_at = timestamp
        publication.cleanup_attempt_count += 1
        publication.last_cleanup_error_json = None
        session.flush()
        return _SharedPublicationCleanupPreparation(
            outcome=None,
            status=publication.status,
            preview=preview,
        )
    if publication.status == "RELEASING":
        publication.cleanup_attempt_count += 1
        publication.cleanup_last_progress_at = _datetime_to_text(now)
        publication.last_cleanup_error_json = None
        session.flush()
        return _SharedPublicationCleanupPreparation(
            outcome=None,
            status=publication.status,
            preview=None,
        )
    evaluated = _evaluate_cleanup_from_session(
        session,
        publication_id=publication_id,
        now=now,
    )
    return _SharedPublicationCleanupPreparation(
        outcome=SharedPublicationCleanupOutcome.BLOCKED,
        status=publication.status,
        preview=evaluated[1] if evaluated is not None else None,
    )


def _list_actionable_table_ref_ids(
    store: RuntimeStore,
    *,
    publication_id: str,
    limit: int,
) -> list[str]:
    with Session(store.engine) as session:
        return list(
            session.scalars(
                _actionable_table_ref_ids_statement(
                    publication_id=publication_id,
                    limit=limit,
                )
            )
        )


def _actionable_table_ref_ids_statement(
    *,
    publication_id: str,
    limit: int,
):
    other_member = aliased(SharedPublicationMemberRecord)
    other_publication = aliased(SharedPublicationRecord)
    referenced_elsewhere = exists(
        select(1)
        .select_from(other_member)
        .join(
            other_publication,
            other_publication.publication_id == other_member.publication_id,
        )
        .where(
            other_member.table_ref_id
            == SharedPublicationMemberRecord.table_ref_id
        )
        .where(other_publication.publication_id != publication_id)
        .where(other_publication.status.in_({"PUBLISHED", "RELEASING"}))
    ).correlate(SharedPublicationMemberRecord)
    return (
        select(SharedPublicationMemberRecord.table_ref_id)
        .join(
            DataRefRecord,
            DataRefRecord.table_ref_id
            == SharedPublicationMemberRecord.table_ref_id,
        )
        .where(SharedPublicationMemberRecord.publication_id == publication_id)
        .where(DataRefRecord.storage_kind == TableStorageKind.RUNTIME_SQL.value)
        .where(
            DataRefRecord.lifecycle_status.in_(
                {
                    LifecycleStatus.PUBLISHED.value,
                    LifecycleStatus.RELEASABLE.value,
                }
            )
        )
        .where(~referenced_elsewhere)
        .distinct()
        .order_by(SharedPublicationMemberRecord.table_ref_id)
        .limit(max(1, limit))
    )


def _finalize_or_record_cleanup_progress_from_session(
    session: Session,
    *,
    publication_id: str,
    now: datetime,
    retry_reasons: list[dict[str, str]],
    max_remaining_count: int,
) -> tuple[bool, int]:
    publication = session.get(SharedPublicationRecord, publication_id)
    if publication is None:
        return False, 0
    if publication.status == "RELEASED":
        return True, 0
    if publication.status != "RELEASING":
        return False, 0
    remaining_ids = list(
        session.scalars(
            _actionable_table_ref_ids_statement(
                publication_id=publication_id,
                limit=max_remaining_count,
            )
        )
    )
    timestamp = _datetime_to_text(now)
    publication.cleanup_last_progress_at = timestamp
    if not remaining_ids:
        publication.status = "RELEASED"
        publication.released_at = timestamp
        publication.last_cleanup_error_json = None
        session.flush()
        return True, 0
    publication.last_cleanup_error_json = _json_dumps(
        {
            "outcome": SharedPublicationCleanupOutcome.RETRY_PENDING.value,
            "remaining_member_count_at_least": len(remaining_ids),
            "failures": retry_reasons[:20],
        }
    )
    session.flush()
    return False, len(remaining_ids)


def _cleanup_member_result(
    result: TableRefReleaseResult,
) -> SharedPublicationCleanupMemberResult:
    return SharedPublicationCleanupMemberResult(
        table_ref_id=result.table_ref_id,
        outcome=result.outcome.value,
        reason=result.reason,
    )


def _interrupted_cleanup_result(
    publication_id: str,
    member_results: tuple[SharedPublicationCleanupMemberResult, ...],
    *,
    status: str | None = "RELEASING",
) -> SharedPublicationCleanupResult:
    return SharedPublicationCleanupResult(
        publication_id=publication_id,
        outcome=SharedPublicationCleanupOutcome.RETRY_PENDING,
        status=status,
        processed_member_count=len(member_results),
        released_member_count=sum(
            result.outcome == TableRefReleaseOutcome.RELEASED.value
            for result in member_results
        ),
        skipped_member_count=sum(
            result.outcome == TableRefReleaseOutcome.SKIPPED.value
            for result in member_results
        ),
        failed_member_count=sum(
            result.outcome == TableRefReleaseOutcome.FAILED.value
            for result in member_results
        ),
        remaining_member_count=1,
        member_results=member_results,
    )


def _release_result_requires_retry(result: TableRefReleaseResult) -> bool:
    if result.outcome == TableRefReleaseOutcome.RELEASED:
        return False
    if result.outcome == TableRefReleaseOutcome.FAILED:
        return True
    return result.reason not in {
        "already_unavailable",
        "external_or_unsupported_storage",
        "shared_publication_active",
        "table_ref_not_found",
    }


def _evaluate_cleanup_from_session(
    session: Session,
    *,
    publication_id: str,
    now: datetime,
) -> tuple[SharedPublicationRecord, SharedPublicationCleanupPreview] | None:
    publication_row = session.execute(
        select(SharedPublicationRecord, WorkflowRunRecord.status)
        .outerjoin(
            WorkflowRunRecord,
            WorkflowRunRecord.workflow_run_id
            == SharedPublicationRecord.producer_run_id,
        )
        .where(SharedPublicationRecord.publication_id == publication_id)
    ).one_or_none()
    if publication_row is None:
        return None
    publication = publication_row.SharedPublicationRecord
    producer_status = publication_row.status
    latest_published_version = session.scalar(
        select(func.max(SharedPublicationRecord.publication_version))
        .where(SharedPublicationRecord.share_name == publication.share_name)
        .where(SharedPublicationRecord.status == "PUBLISHED")
    )
    member_rows = session.execute(
        select(SharedPublicationMemberRecord, DataRefRecord)
        .outerjoin(
            DataRefRecord,
            DataRefRecord.table_ref_id == SharedPublicationMemberRecord.table_ref_id,
        )
        .where(SharedPublicationMemberRecord.publication_id == publication_id)
        .order_by(SharedPublicationMemberRecord.export_name)
    ).all()
    now_text = _datetime_to_text(now)
    active_read_lease_count = int(
        session.scalar(
            select(func.count(ReadLeaseRecord.lease_id))
            .where(ReadLeaseRecord.publication_id == publication_id)
            .where(ReadLeaseRecord.released_at.is_(None))
            .where(ReadLeaseRecord.expires_at > now_text)
        )
        or 0
    )
    active_table_lease_rows = session.execute(
        select(
            TableLeaseRecord.table_ref_id,
            func.count(func.distinct(TableLeaseRecord.lease_id)),
        )
        .join(
            SharedPublicationMemberRecord,
            SharedPublicationMemberRecord.table_ref_id
            == TableLeaseRecord.table_ref_id,
        )
        .where(SharedPublicationMemberRecord.publication_id == publication_id)
        .where(TableLeaseRecord.status == TableLeaseStatus.ACTIVE.value)
        .where(TableLeaseRecord.expires_at > now_text)
        .group_by(TableLeaseRecord.table_ref_id)
    ).all()
    active_table_ref_ids = {str(row[0]) for row in active_table_lease_rows}
    active_table_lease_count = sum(int(row[1]) for row in active_table_lease_rows)
    member_table_ref_ids = {
        member.table_ref_id for member, _table_ref in member_rows
    }
    other_publication_ref_ids: set[str] = set()
    if member_table_ref_ids:
        other_publication_ref_ids = set(
            session.scalars(
                select(SharedPublicationMemberRecord.table_ref_id)
                .join(
                    SharedPublicationRecord,
                    SharedPublicationRecord.publication_id
                    == SharedPublicationMemberRecord.publication_id,
                )
                .where(
                    SharedPublicationMemberRecord.table_ref_id.in_(
                        member_table_ref_ids
                    )
                )
                .where(SharedPublicationRecord.publication_id != publication_id)
                .where(
                    SharedPublicationRecord.status.in_({"PUBLISHED", "RELEASING"})
                )
                .distinct()
            )
        )

    expires_at_invalid = False
    try:
        expires_at = _optional_datetime_from_text(publication.expires_at)
    except ValueError:
        expires_at = None
        expires_at_invalid = True
    is_latest_published = (
        publication.status == "PUBLISHED"
        and publication.publication_version == latest_published_version
    )
    inconsistent = producer_status is None or not member_rows or expires_at_invalid
    member_not_releasable = False
    protected_member_count = 0
    for member, table_ref in member_rows:
        member_inconsistent = (
            table_ref is None
            or table_ref.version != member.exact_table_version
            or table_ref.workflow_run_id != publication.producer_run_id
            or table_ref.mutability
            != TableMutability.PUBLISHED_IMMUTABLE.value
        )
        inconsistent = inconsistent or member_inconsistent
        is_releasable = (
            not member_inconsistent
            and table_ref is not None
            and table_ref.storage_kind == TableStorageKind.RUNTIME_SQL.value
            and table_ref.lifecycle_status == LifecycleStatus.PUBLISHED.value
            and member.table_ref_id not in active_table_ref_ids
            and member.table_ref_id not in other_publication_ref_ids
        )
        if table_ref is not None and (
            table_ref.storage_kind != TableStorageKind.RUNTIME_SQL.value
            or table_ref.lifecycle_status != LifecycleStatus.PUBLISHED.value
        ):
            member_not_releasable = True
        if not is_releasable:
            protected_member_count += 1

    blockers: list[SharedPublicationCleanupBlocker] = []
    if publication.status != "PUBLISHED":
        blockers.append(
            SharedPublicationCleanupBlocker.PUBLICATION_NOT_PUBLISHED
        )
    if expires_at is None:
        blockers.append(SharedPublicationCleanupBlocker.RETENTION_NOT_CONFIGURED)
    elif expires_at > now:
        blockers.append(SharedPublicationCleanupBlocker.RETENTION_NOT_EXPIRED)
    if is_latest_published:
        blockers.append(SharedPublicationCleanupBlocker.LATEST_VERSION_PROTECTED)
    if (
        producer_status is not None
        and producer_status not in TERMINAL_WORKFLOW_STATUS_VALUES
    ):
        blockers.append(SharedPublicationCleanupBlocker.PRODUCER_RUN_ACTIVE)
    if active_read_lease_count:
        blockers.append(SharedPublicationCleanupBlocker.ACTIVE_READ_LEASE)
    if active_table_lease_count:
        blockers.append(SharedPublicationCleanupBlocker.ACTIVE_TABLE_LEASE)
    if other_publication_ref_ids:
        blockers.append(
            SharedPublicationCleanupBlocker.MEMBER_REFERENCED_BY_OTHER_PUBLICATION
        )
    if member_not_releasable:
        blockers.append(SharedPublicationCleanupBlocker.MEMBER_NOT_RELEASABLE)
    if inconsistent:
        blockers.append(SharedPublicationCleanupBlocker.PUBLICATION_INCONSISTENT)

    preview = SharedPublicationCleanupPreview(
        publication_id=publication_id,
        eligible=not blockers,
        status=publication.status,
        expires_at=expires_at,
        is_latest_published=is_latest_published,
        active_read_lease_count=active_read_lease_count,
        active_table_lease_count=active_table_lease_count,
        releasable_member_count=len(member_rows) - protected_member_count,
        protected_member_count=protected_member_count,
        blockers=tuple(blockers),
    )
    return publication, preview

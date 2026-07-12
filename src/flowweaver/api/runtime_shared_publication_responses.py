from __future__ import annotations

from datetime import datetime
from typing import Any

from flowweaver.engine.runtime_models import (
    SharedPublication,
    SharedPublicationCatalogEntry,
    SharedPublicationMember,
    SharedPublicationMemberSummary,
    SharedPublicationSummary,
)
from flowweaver.engine.shared_publication_lifecycle import (
    SharedPublicationCleanupPreview,
    SharedPublicationCleanupResult,
)


def shared_publication_to_jsonable(value: SharedPublication) -> dict[str, Any]:
    return {
        "publication_id": value.publication_id,
        "share_name": value.share_name,
        "publication_version": value.publication_version,
        "producer_workflow_id": value.producer_workflow_id,
        "producer_run_id": value.producer_run_id,
        "status": value.status,
        "input_snapshot_id": value.input_snapshot_id,
        "retention_policy": value.retention_policy,
        "created_at": value.created_at.isoformat(),
        "expires_at": _optional_datetime_to_jsonable(value.expires_at),
        "release_started_at": _optional_datetime_to_jsonable(
            value.release_started_at
        ),
        "cleanup_last_progress_at": _optional_datetime_to_jsonable(
            value.cleanup_last_progress_at
        ),
        "released_at": _optional_datetime_to_jsonable(value.released_at),
        "cleanup_attempt_count": value.cleanup_attempt_count,
        "last_cleanup_error": value.last_cleanup_error,
        "members": [
            {
                "publication_id": member.publication_id,
                "export_name": member.export_name,
                "table_ref_id": member.table_ref_id,
                "exact_table_version": member.exact_table_version,
            }
            for member in value.members
        ],
    }


def shared_publication_catalog_entry_to_jsonable(
    value: SharedPublicationCatalogEntry,
) -> dict[str, Any]:
    return {
        "share_name": value.share_name,
        "latest_published_version": value.latest_published_version,
        "published_version_count": value.published_version_count,
        "latest_member_count": value.latest_member_count,
        "latest_created_at": value.latest_created_at.isoformat(),
    }


def shared_publication_summary_to_jsonable(
    value: SharedPublicationSummary,
) -> dict[str, Any]:
    return {
        "publication_id": value.publication_id,
        "share_name": value.share_name,
        "publication_version": value.publication_version,
        "producer_workflow_id": value.producer_workflow_id,
        "producer_run_id": value.producer_run_id,
        "status": value.status,
        "input_snapshot_id": value.input_snapshot_id,
        "retention_policy": value.retention_policy,
        "created_at": value.created_at.isoformat(),
        "expires_at": _optional_datetime_to_jsonable(value.expires_at),
        "release_started_at": _optional_datetime_to_jsonable(
            value.release_started_at
        ),
        "cleanup_last_progress_at": _optional_datetime_to_jsonable(
            value.cleanup_last_progress_at
        ),
        "released_at": _optional_datetime_to_jsonable(value.released_at),
        "cleanup_attempt_count": value.cleanup_attempt_count,
        "last_cleanup_error": value.last_cleanup_error,
        "member_count": value.member_count,
        "is_latest_published": value.is_latest_published,
    }


def shared_publication_member_to_jsonable(
    value: SharedPublicationMember | SharedPublicationMemberSummary,
) -> dict[str, Any]:
    payload = {
        "publication_id": value.publication_id,
        "export_name": value.export_name,
        "table_ref_id": value.table_ref_id,
        "exact_table_version": value.exact_table_version,
    }
    if isinstance(value, SharedPublicationMemberSummary):
        payload.update(
            {
                "table_ref_lifecycle_status": value.table_ref_lifecycle_status,
                "table_ref_storage_kind": value.table_ref_storage_kind,
                "logical_table_id": value.logical_table_id,
                "can_read_rows": value.can_read_rows,
            }
        )
    return payload


def shared_publication_cleanup_preview_to_jsonable(
    value: SharedPublicationCleanupPreview,
) -> dict[str, Any]:
    return {
        "publication_id": value.publication_id,
        "eligible": value.eligible,
        "status": value.status,
        "expires_at": _optional_datetime_to_jsonable(value.expires_at),
        "is_latest_published": value.is_latest_published,
        "active_read_lease_count": value.active_read_lease_count,
        "active_table_lease_count": value.active_table_lease_count,
        "releasable_member_count": value.releasable_member_count,
        "protected_member_count": value.protected_member_count,
        "blockers": [blocker.value for blocker in value.blockers],
    }


def shared_publication_cleanup_result_to_jsonable(
    value: SharedPublicationCleanupResult,
) -> dict[str, Any]:
    return {
        "publication_id": value.publication_id,
        "outcome": value.outcome.value,
        "status": value.status,
        "processed_member_count": value.processed_member_count,
        "released_member_count": value.released_member_count,
        "skipped_member_count": value.skipped_member_count,
        "failed_member_count": value.failed_member_count,
        "remaining_member_count": value.remaining_member_count,
        "blockers": [blocker.value for blocker in value.blockers],
        "member_results": [
            {
                "table_ref_id": result.table_ref_id,
                "outcome": result.outcome,
                "reason": result.reason,
            }
            for result in value.member_results
        ],
    }


def _optional_datetime_to_jsonable(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

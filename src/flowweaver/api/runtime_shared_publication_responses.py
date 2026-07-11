from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import (
    SharedPublication,
    SharedPublicationCatalogEntry,
    SharedPublicationMember,
    SharedPublicationMemberSummary,
    SharedPublicationSummary,
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

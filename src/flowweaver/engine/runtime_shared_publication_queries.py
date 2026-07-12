from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import (
    DataRefRecord,
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
)
from flowweaver.engine.runtime_models import (
    SharedPublication,
    SharedPublicationCatalogEntry,
    SharedPublicationMemberSummary,
    SharedPublicationSummary,
)
from flowweaver.engine.runtime_record_mappers import (
    _datetime_from_text,
    _datetime_to_text,
    _optional_datetime_from_text,
)
from flowweaver.engine.runtime_shared_table_record_mappers import (
    _shared_publication_from_records,
)
from flowweaver.engine.runtime_shared_table_store_helpers import (
    get_shared_publication_member_records as _get_shared_publication_member_records,
)


def get_shared_publication_from_session(
    session: Session,
    publication_id: str,
) -> SharedPublication | None:
    record = session.get(SharedPublicationRecord, publication_id)
    if record is None:
        return None
    return _shared_publication_from_records(
        record,
        _get_shared_publication_member_records(session, publication_id),
    )


def shared_publication_exists_from_session(
    session: Session,
    publication_id: str,
) -> bool:
    return (
        session.scalar(
            select(SharedPublicationRecord.publication_id)
            .where(SharedPublicationRecord.publication_id == publication_id)
            .limit(1)
        )
        is not None
    )


def get_shared_publication_version_from_session(
    session: Session,
    *,
    share_name: str,
    publication_version: int,
) -> SharedPublication | None:
    record = session.scalar(
        select(SharedPublicationRecord)
        .where(SharedPublicationRecord.share_name == share_name)
        .where(SharedPublicationRecord.publication_version == publication_version)
        .where(SharedPublicationRecord.status == "PUBLISHED")
    )
    if record is None:
        return None
    return _shared_publication_from_records(
        record,
        _get_shared_publication_member_records(session, record.publication_id),
    )


def get_latest_shared_publication_from_session(
    session: Session,
    share_name: str,
) -> SharedPublication | None:
    record = session.scalar(
        select(SharedPublicationRecord)
        .where(SharedPublicationRecord.share_name == share_name)
        .where(SharedPublicationRecord.status == "PUBLISHED")
        .order_by(SharedPublicationRecord.publication_version.desc())
        .limit(1)
    )
    if record is None:
        return None
    return _shared_publication_from_records(
        record,
        _get_shared_publication_member_records(session, record.publication_id),
    )


def list_shared_publications_from_session(
    session: Session,
    *,
    share_name: str | None = None,
    limit: int = 100,
) -> list[SharedPublication]:
    statement = select(SharedPublicationRecord).order_by(
        SharedPublicationRecord.share_name,
        SharedPublicationRecord.publication_version.desc(),
        SharedPublicationRecord.created_at.desc(),
    )
    if share_name is not None:
        statement = statement.where(SharedPublicationRecord.share_name == share_name)
    records = session.scalars(statement.limit(max(1, min(limit, 1000)))).all()
    member_records_by_publication = _member_records_by_publication(
        session,
        [record.publication_id for record in records],
    )
    return [
        _shared_publication_from_records(
            record,
            member_records_by_publication.get(record.publication_id, []),
        )
        for record in records
    ]


def list_shared_publication_catalog_from_session(
    session: Session,
    *,
    query: str | None,
    offset: int,
    limit: int,
) -> list[SharedPublicationCatalogEntry]:
    share_names_statement = (
        select(SharedPublicationRecord.share_name)
        .where(SharedPublicationRecord.status == "PUBLISHED")
        .distinct()
        .order_by(SharedPublicationRecord.share_name)
        .offset(max(0, offset))
        .limit(max(1, min(limit, 1000)))
    )
    if query is not None:
        share_names_statement = share_names_statement.where(
            SharedPublicationRecord.share_name.contains(query)
        )
    share_names = list(session.scalars(share_names_statement))
    if not share_names:
        return []

    aggregation = (
        select(
            SharedPublicationRecord.share_name.label("share_name"),
            func.max(SharedPublicationRecord.publication_version).label(
                "latest_version"
            ),
            func.count(SharedPublicationRecord.publication_id).label(
                "version_count"
            ),
        )
        .where(SharedPublicationRecord.status == "PUBLISHED")
        .where(SharedPublicationRecord.share_name.in_(share_names))
        .group_by(SharedPublicationRecord.share_name)
        .subquery()
    )
    rows = session.execute(
        select(
            SharedPublicationRecord,
            aggregation.c.version_count,
        )
        .join(
            aggregation,
            and_(
                SharedPublicationRecord.share_name == aggregation.c.share_name,
                SharedPublicationRecord.publication_version
                == aggregation.c.latest_version,
            ),
        )
        .where(SharedPublicationRecord.status == "PUBLISHED")
        .order_by(SharedPublicationRecord.share_name)
    ).all()
    member_counts = _member_counts_by_publication(
        session,
        [row.SharedPublicationRecord.publication_id for row in rows],
    )
    return [
        SharedPublicationCatalogEntry(
            share_name=row.SharedPublicationRecord.share_name,
            latest_published_version=row.SharedPublicationRecord.publication_version,
            published_version_count=int(row.version_count),
            latest_member_count=member_counts.get(
                row.SharedPublicationRecord.publication_id,
                0,
            ),
            latest_created_at=_datetime_from_text(
                row.SharedPublicationRecord.created_at
            ),
        )
        for row in rows
    ]


def count_shared_publication_catalog_from_session(
    session: Session,
    *,
    query: str | None,
) -> int:
    statement = select(
        func.count(func.distinct(SharedPublicationRecord.share_name))
    ).where(
        SharedPublicationRecord.status == "PUBLISHED",
    )
    if query is not None:
        statement = statement.where(
            SharedPublicationRecord.share_name.contains(query)
        )
    return int(session.scalar(statement) or 0)


def list_shared_publication_summaries_from_session(
    session: Session,
    *,
    share_name: str,
    offset: int,
    limit: int,
) -> list[SharedPublicationSummary]:
    records = session.scalars(
        select(SharedPublicationRecord)
        .where(SharedPublicationRecord.share_name == share_name)
        .order_by(SharedPublicationRecord.publication_version.desc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 1000)))
    ).all()
    if not records:
        return []
    latest_version = session.scalar(
        select(func.max(SharedPublicationRecord.publication_version))
        .where(SharedPublicationRecord.share_name == share_name)
        .where(SharedPublicationRecord.status == "PUBLISHED")
    )
    member_counts = _member_counts_by_publication(
        session,
        [record.publication_id for record in records],
    )
    return [
        SharedPublicationSummary(
            publication_id=record.publication_id,
            share_name=record.share_name,
            publication_version=record.publication_version,
            producer_workflow_id=record.producer_workflow_id,
            producer_run_id=record.producer_run_id,
            status=record.status,
            input_snapshot_id=record.input_snapshot_id,
            retention_policy=json.loads(record.retention_policy_json),
            created_at=_datetime_from_text(record.created_at),
            expires_at=_optional_datetime_from_text(record.expires_at),
            release_started_at=_optional_datetime_from_text(
                record.release_started_at
            ),
            cleanup_last_progress_at=_optional_datetime_from_text(
                record.cleanup_last_progress_at
            ),
            released_at=_optional_datetime_from_text(record.released_at),
            cleanup_attempt_count=record.cleanup_attempt_count,
            last_cleanup_error=(
                json.loads(record.last_cleanup_error_json)
                if record.last_cleanup_error_json is not None
                else None
            ),
            member_count=member_counts.get(record.publication_id, 0),
            is_latest_published=(
                record.status == "PUBLISHED"
                and record.publication_version == latest_version
            ),
        )
        for record in records
    ]


def count_shared_publication_versions_from_session(
    session: Session,
    *,
    share_name: str,
) -> int:
    return int(
        session.scalar(
            select(func.count(SharedPublicationRecord.publication_id)).where(
                SharedPublicationRecord.share_name == share_name
            )
        )
        or 0
    )


def list_expired_shared_publication_ids_from_session(
    session: Session,
    *,
    now: datetime,
    limit: int,
) -> list[str]:
    return list(
        session.scalars(
            select(SharedPublicationRecord.publication_id)
            .where(SharedPublicationRecord.status == "PUBLISHED")
            .where(SharedPublicationRecord.expires_at.is_not(None))
            .where(SharedPublicationRecord.expires_at <= _datetime_to_text(now))
            .order_by(
                SharedPublicationRecord.expires_at,
                SharedPublicationRecord.publication_id,
            )
            .limit(max(1, min(limit, 1000)))
        )
    )


def list_shared_publication_members_from_session(
    session: Session,
    *,
    publication_id: str,
    offset: int,
    limit: int,
) -> list[SharedPublicationMemberSummary]:
    rows = session.execute(
        select(SharedPublicationMemberRecord, DataRefRecord)
        .join(
            DataRefRecord,
            DataRefRecord.table_ref_id == SharedPublicationMemberRecord.table_ref_id,
        )
        .where(SharedPublicationMemberRecord.publication_id == publication_id)
        .order_by(SharedPublicationMemberRecord.export_name)
        .offset(max(0, offset))
        .limit(max(1, min(limit, 1000)))
    ).all()
    return [
        SharedPublicationMemberSummary(
            publication_id=member_record.publication_id,
            export_name=member_record.export_name,
            table_ref_id=member_record.table_ref_id,
            exact_table_version=member_record.exact_table_version,
            table_ref_lifecycle_status=table_ref_record.lifecycle_status,
            table_ref_storage_kind=table_ref_record.storage_kind,
            logical_table_id=table_ref_record.logical_table_id,
            can_read_rows=_data_ref_record_can_read_rows(table_ref_record),
        )
        for member_record, table_ref_record in rows
    ]


def _data_ref_record_can_read_rows(record: DataRefRecord) -> bool:
    capabilities = json.loads(record.capabilities_json)
    return "READ" in capabilities and record.lifecycle_status not in {
        "RELEASABLE",
        "RELEASED",
        "RETIRED",
        "ORPHANED",
    }


def count_shared_publication_members_from_session(
    session: Session,
    *,
    publication_id: str,
) -> int:
    return int(
        session.scalar(
            select(func.count(SharedPublicationMemberRecord.export_name)).where(
                SharedPublicationMemberRecord.publication_id == publication_id
            )
        )
        or 0
    )


def _member_records_by_publication(
    session: Session,
    publication_ids: list[str],
) -> dict[str, list[SharedPublicationMemberRecord]]:
    if not publication_ids:
        return {}
    grouped: defaultdict[str, list[SharedPublicationMemberRecord]] = defaultdict(list)
    records = session.scalars(
        select(SharedPublicationMemberRecord)
        .where(SharedPublicationMemberRecord.publication_id.in_(publication_ids))
        .order_by(
            SharedPublicationMemberRecord.publication_id,
            SharedPublicationMemberRecord.export_name,
        )
    ).all()
    for record in records:
        grouped[record.publication_id].append(record)
    return dict(grouped)


def _member_counts_by_publication(
    session: Session,
    publication_ids: list[str],
) -> dict[str, int]:
    if not publication_ids:
        return {}
    rows = session.execute(
        select(
            SharedPublicationMemberRecord.publication_id,
            func.count(SharedPublicationMemberRecord.export_name),
        )
        .where(SharedPublicationMemberRecord.publication_id.in_(publication_ids))
        .group_by(SharedPublicationMemberRecord.publication_id)
    ).all()
    return {publication_id: int(count) for publication_id, count in rows}

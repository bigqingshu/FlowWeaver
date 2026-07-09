from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import SharedPublicationRecord
from flowweaver.engine.runtime_models import SharedPublication
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
    return [
        _shared_publication_from_records(
            record,
            _get_shared_publication_member_records(session, record.publication_id),
        )
        for record in records
    ]

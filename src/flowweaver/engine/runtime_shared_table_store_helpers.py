from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from flowweaver.engine.db_models import (
    SharedPublicationMemberRecord,
    SharedPublicationRecord,
)
from flowweaver.engine.runtime_models import InputSnapshotEntry


def get_shared_publication_member_records(
    session: Session,
    publication_id: str,
) -> list[SharedPublicationMemberRecord]:
    return list(
        session.scalars(
            select(SharedPublicationMemberRecord)
            .where(SharedPublicationMemberRecord.publication_id == publication_id)
            .order_by(SharedPublicationMemberRecord.export_name)
        ).all()
    )


def validate_input_snapshot_publications(
    session: Session,
    inputs: tuple[InputSnapshotEntry, ...],
) -> None:
    for item in inputs:
        publication = session.get(
            SharedPublicationRecord,
            item.publication_id,
        )
        if publication is None:
            raise ValueError(
                f"Input snapshot publication not found: {item.publication_id}"
            )
        if publication.publication_version != item.publication_version:
            raise ValueError(
                f"Input snapshot publication version mismatch: {item.publication_id}"
            )

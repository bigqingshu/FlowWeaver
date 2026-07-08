from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from flowweaver.engine.runtime_models import (
    InputSnapshot,
    InputSnapshotEntry,
    ReadLease,
    SharedPublication,
    SharedPublicationMember,
)
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.protocols.table_ref import TableRefModel


class SharedTableVersionPolicy(str, Enum):
    LATEST = "LATEST"
    EXACT_VERSION = "EXACT_VERSION"


@dataclass(frozen=True)
class SharedTableReadResult:
    publication: SharedPublication
    table_refs: tuple[TableRefModel, ...]
    input_snapshot: InputSnapshot
    read_lease: ReadLease


class SharedTableReader:
    def __init__(self, store: RuntimeStore) -> None:
        self._store = store

    def read(
        self,
        *,
        consumer_workflow_run_id: str,
        share_name: str,
        version_policy: SharedTableVersionPolicy | str,
        exact_version: int | None = None,
        selected_members: tuple[str, ...] | None = None,
        lease_expires_at: datetime,
    ) -> SharedTableReadResult:
        policy = SharedTableVersionPolicy(version_policy)
        publication = self._resolve_publication(
            share_name=share_name,
            version_policy=policy,
            exact_version=exact_version,
        )
        members = self._select_members(
            publication=publication,
            selected_members=selected_members,
        )
        table_refs = tuple(self._load_table_refs(members))
        input_snapshot, read_lease = self._store.create_input_snapshot_and_read_lease(
            workflow_run_id=consumer_workflow_run_id,
            inputs=[
                InputSnapshotEntry(
                    source_name=share_name,
                    publication_id=publication.publication_id,
                    publication_version=publication.publication_version,
                    selected_members=tuple(member.export_name for member in members),
                )
            ],
            publication_id=publication.publication_id,
            publication_version=publication.publication_version,
            selected_members=tuple(member.export_name for member in members),
            expires_at=lease_expires_at,
        )
        return SharedTableReadResult(
            publication=publication,
            table_refs=table_refs,
            input_snapshot=input_snapshot,
            read_lease=read_lease,
        )

    def _resolve_publication(
        self,
        *,
        share_name: str,
        version_policy: SharedTableVersionPolicy,
        exact_version: int | None,
    ) -> SharedPublication:
        if version_policy == SharedTableVersionPolicy.LATEST:
            publication = self._store.get_latest_shared_publication(share_name)
        elif version_policy == SharedTableVersionPolicy.EXACT_VERSION:
            if exact_version is None:
                raise ValueError("EXACT_VERSION requires exact_version")
            publication = self._store.get_shared_publication_version(
                share_name=share_name,
                publication_version=exact_version,
            )
        else:
            raise ValueError(
                f"Unsupported shared table version policy: {version_policy}"
            )
        if publication is None:
            raise ValueError(f"Shared publication not found: {share_name}")
        return publication

    def _select_members(
        self,
        *,
        publication: SharedPublication,
        selected_members: tuple[str, ...] | None,
    ) -> tuple[SharedPublicationMember, ...]:
        member_by_name = {member.export_name: member for member in publication.members}
        if selected_members is None:
            return publication.members
        missing = [name for name in selected_members if name not in member_by_name]
        if missing:
            raise ValueError(
                "Shared publication members not found: " + ",".join(sorted(missing))
            )
        return tuple(member_by_name[name] for name in selected_members)

    def _load_table_refs(
        self,
        members: tuple[SharedPublicationMember, ...],
    ) -> list[TableRefModel]:
        table_refs: list[TableRefModel] = []
        for member in members:
            table_ref = self._store.get_table_ref(member.table_ref_id)
            if table_ref is None:
                raise ValueError(f"TableRef not found: {member.table_ref_id}")
            if table_ref.version != member.exact_table_version:
                raise ValueError(
                    "TableRef version mismatch for shared publication member: "
                    f"{member.export_name}"
                )
            table_refs.append(table_ref)
        return table_refs

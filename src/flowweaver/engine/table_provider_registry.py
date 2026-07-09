from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from flowweaver.engine.external_sql_table_provider import (
    SQLiteExternalSqlTableProvider,
)
from flowweaver.engine.memory_table_provider import MemoryTableProvider
from flowweaver.engine.runtime_table_provider import (
    SQLiteRuntimeTableProvider,
)
from flowweaver.engine.table_provider_protocol import TableProvider
from flowweaver.protocols.enums import TableStorageKind


@dataclass(frozen=True)
class TableProviderRegistration:
    provider: TableProvider
    storage_kinds: frozenset[TableStorageKind]


class TableProviderRegistry:
    def __init__(
        self,
        registrations: Iterable[TableProviderRegistration] = (),
    ) -> None:
        self._registrations: dict[str, TableProviderRegistration] = {}
        for registration in registrations:
            self.register(
                registration.provider,
                storage_kinds=registration.storage_kinds,
            )

    def register(
        self,
        provider: TableProvider,
        *,
        storage_kinds: Iterable[TableStorageKind],
    ) -> None:
        if provider.provider_id in self._registrations:
            raise ValueError(f"Duplicate table provider: {provider.provider_id}")
        storage_kind_set = frozenset(storage_kinds)
        if not storage_kind_set:
            raise ValueError("table provider must support at least one storage kind")
        self._registrations[provider.provider_id] = TableProviderRegistration(
            provider=provider,
            storage_kinds=storage_kind_set,
        )

    def get(self, provider_id: str) -> TableProvider | None:
        registration = self._registrations.get(provider_id)
        return registration.provider if registration is not None else None

    def supports_storage_kind(
        self,
        provider_id: str,
        storage_kind: TableStorageKind,
    ) -> bool:
        registration = self._registrations.get(provider_id)
        return (
            registration is not None
            and storage_kind in registration.storage_kinds
        )


def create_default_table_provider_registry(
    runtime_dir: str | Path,
    *,
    runtime_provider: SQLiteRuntimeTableProvider | None = None,
    memory_provider: MemoryTableProvider | None = None,
) -> TableProviderRegistry:
    registry = TableProviderRegistry()
    registry.register(
        runtime_provider or SQLiteRuntimeTableProvider(runtime_dir),
        storage_kinds=(TableStorageKind.RUNTIME_SQL,),
    )
    registry.register(
        SQLiteExternalSqlTableProvider(),
        storage_kinds=(TableStorageKind.EXTERNAL_SQL,),
    )
    registry.register(
        memory_provider or MemoryTableProvider(),
        storage_kinds=(TableStorageKind.MEMORY,),
    )
    return registry

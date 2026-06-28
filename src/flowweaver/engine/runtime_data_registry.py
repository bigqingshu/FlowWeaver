from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.protocols.enums import LifecycleStatus, TableMutability
from flowweaver.protocols.table_ref import TableRefModel


class RuntimeDataRegistry:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        table_provider: SQLiteRuntimeTableProvider,
    ) -> None:
        self._store = store
        self._table_provider = table_provider

    def register_staging(self, table_ref: TableRefModel) -> None:
        self._ensure_staging_ref(table_ref)
        self._store.register_table_ref(table_ref)

    def publish(self, staging_table_ref_id: str) -> TableRefModel:
        staging_ref = self.get(staging_table_ref_id)
        self._ensure_staging_ref(staging_ref)
        published_ref = self._table_provider.published_ref_from_staging(staging_ref)
        self._table_provider.publish_staging(staging_ref, published_ref)
        self._store.register_table_ref(published_ref)
        return published_ref

    def get(self, table_ref_id: str) -> TableRefModel:
        table_ref = self._store.get_table_ref(table_ref_id)
        if table_ref is None:
            raise KeyError(table_ref_id)
        return table_ref

    def list_by_workflow_run(self, workflow_run_id: str) -> list[TableRefModel]:
        return self._store.list_table_refs_by_workflow_run(workflow_run_id)

    def _ensure_staging_ref(self, table_ref: TableRefModel) -> None:
        if table_ref.provider_id != self._table_provider.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.lifecycle_status != LifecycleStatus.STAGING:
            raise ValueError("RuntimeDataRegistry requires a STAGING table_ref")
        if table_ref.mutability != TableMutability.WORKING_MUTABLE:
            raise ValueError("STAGING table_ref must be WORKING_MUTABLE")

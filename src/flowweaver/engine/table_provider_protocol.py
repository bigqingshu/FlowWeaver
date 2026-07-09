from __future__ import annotations

from typing import Any, Protocol

from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class TableProvider(Protocol):
    provider_id: str

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        ...

    def count_rows(self, table_ref: TableRefModel) -> int:
        ...

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    def create_table(self, table_ref: TableRefModel) -> None:
        ...

    def drop_table(self, table_ref: TableRefModel) -> None:
        ...

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        ...

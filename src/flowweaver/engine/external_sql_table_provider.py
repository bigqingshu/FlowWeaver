from __future__ import annotations

from pathlib import Path
from typing import Any

from flowweaver.engine.external_sql_table_reading import (
    count_external_sql_rows as _count_external_sql_rows,
)
from flowweaver.engine.external_sql_table_reading import (
    quote_external_sql_identifier as _quote_identifier,
)
from flowweaver.engine.external_sql_table_reading import (
    read_external_sql_rows as _read_external_sql_rows,
)
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

EXTERNAL_SQL_PROVIDER_ID = "external_sql"


class SQLiteExternalSqlTableProvider:
    provider_id = EXTERNAL_SQL_PROVIDER_ID

    def get_schema(self, table_ref: TableRefModel) -> list[FieldSchemaModel]:
        self._validate_ref(table_ref)
        return list(table_ref.schema)

    def count_rows(self, table_ref: TableRefModel) -> int:
        database_path, source_sql = self._source(table_ref)
        return _count_external_sql_rows(database_path, source_sql)

    def read_rows(
        self,
        table_ref: TableRefModel,
        offset: int,
        limit: int,
        columns: list[str] | None = None,
        order_by: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        database_path, source_sql = self._source(table_ref)
        return _read_external_sql_rows(
            table_ref=table_ref,
            database_path=database_path,
            source_sql=source_sql,
            offset=offset,
            limit=limit,
            columns=columns,
            order_by=order_by,
            filters=filters,
        )

    def create_table(self, table_ref: TableRefModel) -> None:
        raise ValueError("external SQL provider is read-only")

    def drop_table(self, table_ref: TableRefModel) -> None:
        raise ValueError("external SQL provider is read-only")

    def publish_staging(
        self,
        staging_ref: TableRefModel,
        published_ref: TableRefModel,
    ) -> None:
        raise ValueError("external SQL provider is read-only")

    def _source(self, table_ref: TableRefModel) -> tuple[Path, str]:
        self._validate_ref(table_ref)
        database_path_value = table_ref.opaque_handle.get("database_path")
        if not isinstance(database_path_value, str) or not database_path_value:
            raise ValueError(
                "external SQL table_ref opaque_handle.database_path is required"
            )
        database_path = Path(database_path_value)
        if not database_path.exists():
            raise ValueError("external SQL database does not exist")

        table_name = table_ref.opaque_handle.get("table_name")
        query = table_ref.opaque_handle.get("query")
        if isinstance(table_name, str) and table_name and query is None:
            return database_path, _quote_identifier(table_name)
        if isinstance(query, str) and query and table_name is None:
            normalized_query = query.strip()
            if not normalized_query.lower().startswith("select "):
                raise ValueError("external SQL query must be a SELECT statement")
            if ";" in normalized_query:
                raise ValueError("external SQL query must not contain semicolons")
            return database_path, f"({normalized_query}) AS external_source"
        raise ValueError(
            "external SQL table_ref requires exactly one of table_name or query"
        )

    def _validate_ref(self, table_ref: TableRefModel) -> None:
        if table_ref.provider_id != self.provider_id:
            raise ValueError("table_ref belongs to a different provider")
        if table_ref.storage_kind != TableStorageKind.EXTERNAL_SQL:
            raise ValueError("external SQL provider only supports EXTERNAL_SQL")

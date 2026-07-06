from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.external_sql_table_provider import EXTERNAL_SQL_PROVIDER_ID
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import schema_fingerprint
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

SQL_MAPPING_NODE_TYPE = "SqlMappingNode"


class SqlMappingNodeRunner:
    def __init__(self, *, store: RuntimeStore) -> None:
        self._store = store

    def execute(self, task_config: SqlMappingTaskConfig) -> TableRefModel:
        opaque_handle = task_config.opaque_handle()
        schema = task_config.schema or _infer_schema(
            database_path=task_config.database_path,
            table_name=task_config.table_name,
            query=task_config.query,
        )
        table_ref = TableRefModel(
            table_ref_id=new_id(),
            role=TableRole.CURRENT,
            storage_kind=TableStorageKind.EXTERNAL_SQL,
            scope=TableScope.WORKFLOW_SCOPE,
            mutability=TableMutability.PUBLISHED_IMMUTABLE,
            provider_id=EXTERNAL_SQL_PROVIDER_ID,
            logical_table_id=task_config.logical_table_id,
            opaque_handle=opaque_handle,
            schema=schema,
            schema_fingerprint=schema_fingerprint(schema),
            version=task_config.version,
            capabilities={"READ"},
            lifecycle_status=LifecycleStatus.PUBLISHED,
            created_by_workflow_run_id=task_config.workflow_run_id,
            created_by_node_run_id=task_config.node_run_id,
            created_at=utc_now(),
        )
        self._store.register_table_ref(table_ref)
        return table_ref


class SqlMappingTaskConfig:
    def __init__(
        self,
        *,
        workflow_run_id: str,
        node_run_id: str,
        node_instance_id: str,
        config: dict[str, Any],
    ) -> None:
        self.workflow_run_id = workflow_run_id
        self.node_run_id = node_run_id
        self.node_instance_id = node_instance_id
        self.database_path = _required_path_config(config, "database_path")
        self.table_name = _optional_str_config(config, "table_name")
        self.query = _optional_str_config(config, "query")
        if bool(self.table_name) == bool(self.query):
            raise ValueError(
                "SqlMappingNode requires exactly one of table_name or query"
            )
        self.logical_table_id = (
            _optional_str_config(config, "logical_table_id")
            or self.table_name
            or self.node_instance_id
        )
        self.version = _optional_int_config(config, "version") or 1
        self.schema = _optional_schema_config(config, "schema")

    def opaque_handle(self) -> dict[str, str]:
        handle = {"database_path": self.database_path.as_posix()}
        if self.table_name is not None:
            handle["table_name"] = self.table_name
        if self.query is not None:
            handle["query"] = _normalize_query(self.query)
        return handle


def _required_path_config(config: dict[str, Any], key: str) -> Path:
    value = config.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    path = Path(value)
    if not path.exists():
        raise ValueError(f"config.{key} does not exist")
    return path


def _optional_str_config(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"config.{key} must be a non-empty string")
    return value


def _optional_int_config(config: dict[str, Any], key: str) -> int | None:
    value = config.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"config.{key} must be an integer")
    if value < 1:
        raise ValueError(f"config.{key} must be positive")
    return value


def _optional_schema_config(
    config: dict[str, Any],
    key: str,
) -> list[FieldSchemaModel] | None:
    value = config.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not value:
        raise ValueError(f"config.{key} must be a non-empty list")
    schema: list[FieldSchemaModel] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"config.{key}[{index}] must be an object")
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"config.{key}[{index}].name must be a non-empty string")
        data_type = item.get("data_type", "TEXT")
        if not isinstance(data_type, str) or not data_type:
            raise ValueError(
                f"config.{key}[{index}].data_type must be a non-empty string"
            )
        nullable = item.get("nullable", True)
        if not isinstance(nullable, bool):
            raise ValueError(f"config.{key}[{index}].nullable must be a boolean")
        field_id = item.get("field_id", name)
        if not isinstance(field_id, str) or not field_id:
            raise ValueError(f"config.{key}[{index}].field_id must be a string")
        schema.append(
            FieldSchemaModel(
                field_id=field_id,
                name=name,
                data_type=_normalize_data_type(data_type),
                nullable=nullable,
                ordinal=index,
            )
        )
    return schema


def _infer_schema(
    *,
    database_path: Path,
    table_name: str | None,
    query: str | None,
) -> list[FieldSchemaModel]:
    if table_name is not None:
        return _infer_table_schema(database_path, table_name)
    assert query is not None
    return _infer_query_schema(database_path, query)


def _infer_table_schema(database_path: Path, table_name: str) -> list[FieldSchemaModel]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            f"PRAGMA table_info({_quote_sql_string(table_name)})"
        ).fetchall()
    if not rows:
        raise ValueError(f"table does not exist or has no columns: {table_name}")
    return [
        FieldSchemaModel(
            field_id=str(row[1]),
            name=str(row[1]),
            data_type=_normalize_data_type(str(row[2] or "TEXT")),
            nullable=not bool(row[3]),
            ordinal=index,
        )
        for index, row in enumerate(rows)
    ]


def _infer_query_schema(database_path: Path, query: str) -> list[FieldSchemaModel]:
    normalized_query = _normalize_query(query)
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(f"SELECT * FROM ({normalized_query}) LIMIT 0")
        columns = [item[0] for item in cursor.description or []]
    if not columns:
        raise ValueError("query must return at least one column")
    return [
        FieldSchemaModel(
            field_id=str(column),
            name=str(column),
            data_type="TEXT",
            nullable=True,
            ordinal=index,
        )
        for index, column in enumerate(columns)
    ]


def _normalize_query(query: str) -> str:
    normalized_query = query.strip()
    if not normalized_query.lower().startswith("select "):
        raise ValueError("config.query must be a SELECT statement")
    if ";" in normalized_query:
        raise ValueError("config.query must not contain semicolons")
    return normalized_query


def _normalize_data_type(value: str) -> str:
    normalized = value.upper()
    if "INT" in normalized:
        return "INTEGER"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB", "NUM")):
        return "FLOAT"
    if "BOOL" in normalized:
        return "BOOLEAN"
    return "TEXT"


def _quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

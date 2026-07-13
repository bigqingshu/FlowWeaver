from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_sql_config_fields import (
    optional_int_config as _optional_int_config,
)
from flowweaver.nodes.builtin_sql_config_fields import (
    optional_schema_config as _optional_schema_config,
)
from flowweaver.nodes.builtin_sql_config_fields import (
    optional_str_config as _optional_str_config,
)
from flowweaver.nodes.builtin_sql_config_fields import (
    required_path_config as _required_path_config,
)
from flowweaver.nodes.builtin_sql_schema import infer_schema as infer_schema
from flowweaver.nodes.builtin_sql_schema import (
    normalize_data_type as normalize_data_type,
)
from flowweaver.nodes.builtin_sql_schema import normalize_query as normalize_query

SQL_SOURCE_MODE_TABLE = "table"
SQL_SOURCE_MODE_ALL_TABLES = "all_tables"
SQL_SOURCE_MODE_QUERY = "query"
SQL_SOURCE_MODES = {
    SQL_SOURCE_MODE_TABLE,
    SQL_SOURCE_MODE_ALL_TABLES,
    SQL_SOURCE_MODE_QUERY,
}


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
        source_mode = _optional_str_config(config, "source_mode")
        if source_mode is None and bool(self.table_name) == bool(self.query):
            raise ValueError(
                "SqlMappingNode requires exactly one of table_name or query"
            )
        self.source_mode = source_mode or (
            SQL_SOURCE_MODE_QUERY if self.query is not None else SQL_SOURCE_MODE_TABLE
        )
        if self.source_mode not in SQL_SOURCE_MODES:
            raise ValueError(f"unsupported source_mode: {self.source_mode}")

        logical_table_id = _optional_str_config(config, "logical_table_id")
        self.version = _optional_int_config(config, "version") or 1
        self.schema = _optional_schema_config(config, "schema")
        self.logical_table_id: str | None

        if self.source_mode == SQL_SOURCE_MODE_TABLE:
            if self.table_name is None or self.query is not None:
                raise ValueError(
                    "SqlMappingNode table mode requires table_name and no query"
                )
            self.logical_table_id = logical_table_id or self.table_name
        elif self.source_mode == SQL_SOURCE_MODE_QUERY:
            if self.query is None or self.table_name is not None:
                raise ValueError(
                    "SqlMappingNode query mode requires query and no table_name"
                )
            self.logical_table_id = logical_table_id or self.node_instance_id
        else:
            if self.table_name is not None or self.query is not None:
                raise ValueError(
                    "SqlMappingNode all_tables mode does not accept table_name or query"
                )
            if logical_table_id is not None:
                raise ValueError(
                    "SqlMappingNode all_tables mode does not accept logical_table_id"
                )
            if self.schema is not None:
                raise ValueError(
                    "SqlMappingNode all_tables mode does not accept schema"
                )
            self.logical_table_id = None

    def opaque_handle(self, *, table_name: str | None = None) -> dict[str, str]:
        handle = {"database_path": self.database_path.as_posix()}
        selected_table_name = table_name or self.table_name
        if selected_table_name is not None:
            handle["table_name"] = selected_table_name
        if self.query is not None:
            handle["query"] = normalize_query(self.query)
        return handle

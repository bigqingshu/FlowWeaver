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
            handle["query"] = normalize_query(self.query)
        return handle

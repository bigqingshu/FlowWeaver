from __future__ import annotations

from flowweaver.common.ids import new_id
from flowweaver.common.time import utc_now
from flowweaver.engine.external_sql_table_provider import EXTERNAL_SQL_PROVIDER_ID
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import schema_fingerprint
from flowweaver.nodes.builtin_sql_config import (
    SQL_SOURCE_MODE_ALL_TABLES,
)
from flowweaver.nodes.builtin_sql_config import (
    SqlMappingTaskConfig as SqlMappingTaskConfig,
)
from flowweaver.nodes.builtin_sql_config import infer_schema as _infer_schema
from flowweaver.nodes.builtin_sql_schema import infer_all_table_schemas
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

    def execute(self, task_config: SqlMappingTaskConfig) -> list[TableRefModel]:
        if task_config.source_mode == SQL_SOURCE_MODE_ALL_TABLES:
            table_schemas = infer_all_table_schemas(task_config.database_path)
            if not table_schemas:
                raise ValueError("SQLite database contains no user tables")
            return [
                self._register_table_ref(
                    task_config,
                    logical_table_id=table_name,
                    opaque_handle=task_config.opaque_handle(table_name=table_name),
                    schema=schema,
                )
                for table_name, schema in table_schemas
            ]

        schema = task_config.schema or _infer_schema(
            database_path=task_config.database_path,
            table_name=task_config.table_name,
            query=task_config.query,
        )
        assert task_config.logical_table_id is not None
        return [
            self._register_table_ref(
                task_config,
                logical_table_id=task_config.logical_table_id,
                opaque_handle=task_config.opaque_handle(),
                schema=schema,
            )
        ]

    def _register_table_ref(
        self,
        task_config: SqlMappingTaskConfig,
        *,
        logical_table_id: str,
        opaque_handle: dict[str, str],
        schema: list[FieldSchemaModel],
    ) -> TableRefModel:
        table_ref = TableRefModel(
            table_ref_id=new_id(),
            role=TableRole.CURRENT,
            storage_kind=TableStorageKind.EXTERNAL_SQL,
            scope=TableScope.WORKFLOW_SCOPE,
            mutability=TableMutability.PUBLISHED_IMMUTABLE,
            provider_id=EXTERNAL_SQL_PROVIDER_ID,
            logical_table_id=logical_table_id,
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

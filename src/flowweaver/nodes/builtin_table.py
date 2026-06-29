from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_data_registry import RuntimeDataRegistry
from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.engine.runtime_table_provider import SQLiteRuntimeTableProvider
from flowweaver.nodes.permission_checks import (
    PermissionCheckError,
    ensure_task_permission_scope,
)
from flowweaver.protocols.enums import ErrorOrigin, NodeResultStatus, PermissionAction
from flowweaver.protocols.node_task import NodeTaskModel, NodeTaskResultModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

GENERATE_TEST_TABLE_NODE_TYPE = "GenerateTestTableNode"
FILTER_ROWS_NODE_TYPE = "FilterRowsNode"


def table_node_types() -> tuple[str, str]:
    return (GENERATE_TEST_TABLE_NODE_TYPE, FILTER_ROWS_NODE_TYPE)


def is_table_node_type(node_type: str) -> bool:
    return node_type in table_node_types()


class BuiltinTableNodeRunner:
    def __init__(
        self,
        *,
        store: RuntimeStore,
        registry: RuntimeDataRegistry,
        table_provider: SQLiteRuntimeTableProvider,
    ) -> None:
        self._store = store
        self._registry = registry
        self._table_provider = table_provider

    def execute(
        self,
        task: NodeTaskModel,
        *,
        executor_id: str,
    ) -> NodeTaskResultModel:
        started_at = utc_now()
        try:
            if task.node_type == GENERATE_TEST_TABLE_NODE_TYPE:
                output_refs = self._execute_generate(task)
            elif task.node_type == FILTER_ROWS_NODE_TYPE:
                output_refs = self._execute_filter(task)
            else:
                raise _NodeValidationError(
                    f"Unsupported builtin node type: {task.node_type}"
                )
        except (_NodeValidationError, PermissionCheckError) as exc:
            return NodeTaskResultModel(
                task_id=task.task_id,
                node_run_id=task.node_run_id,
                attempt=task.attempt,
                executor_id=executor_id,
                process_generation=task.process_generation,
                status=NodeResultStatus.FAILED,
                error={
                    "error_code": "VALIDATION_ERROR",
                    "message": str(exc),
                    "origin": ErrorOrigin.NODE.value,
                },
                started_at=started_at,
                finished_at=utc_now(),
            )
        return NodeTaskResultModel(
            task_id=task.task_id,
            node_run_id=task.node_run_id,
            attempt=task.attempt,
            executor_id=executor_id,
            process_generation=task.process_generation,
            status=NodeResultStatus.SUCCEEDED,
            output_refs=[table_ref.table_ref_id for table_ref in output_refs],
            started_at=started_at,
            finished_at=utc_now(),
        )

    def _execute_generate(self, task: NodeTaskModel) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("GenerateTestTableNode does not accept inputs")
        rows_count = _int_config(task.config, "rows")
        seed = _int_config(task.config, "seed", default=0)
        schema = _parse_columns(task.config.get("columns"))
        rows = [
            {
                field.name: _generated_value(field, row_number=row_number, seed=seed)
                for field in schema
            }
            for row_number in range(1, rows_count + 1)
        ]
        return [
            self._publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=schema,
                rows=rows,
            )
        ]

    def _execute_filter(self, task: NodeTaskModel) -> list[TableRefModel]:
        if len(task.input_refs) != 1:
            raise _NodeValidationError("FilterRowsNode requires exactly one input_ref")
        input_ref = self._registry.get(task.input_refs[0])
        field = task.config.get("field")
        if not isinstance(field, str) or not field:
            raise _NodeValidationError("FilterRowsNode config.field is required")
        schema_field_names = {item.name for item in input_ref.schema}
        if field not in schema_field_names:
            raise _NodeValidationError(f"Field does not exist: {field}")
        operator = _normalize_operator(task.config.get("operator"))
        value = task.config.get("value")
        rows = self._table_provider.read_rows(
            input_ref,
            offset=0,
            limit=self._table_provider.count_rows(input_ref),
        )
        filtered_rows = [
            row
            for row in rows
            if _row_matches(row.get(field), operator=operator, value=value)
        ]
        return [
            self._publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=input_ref.schema,
                rows=filtered_rows,
            )
        ]

    def _publish_rows(
        self,
        task: NodeTaskModel,
        *,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableRefModel:
        ensure_task_permission_scope(
            store=self._store,
            task=task,
            action=PermissionAction.PUBLISH,
            resource_type="NODE_OUTPUT",
            resource_id=_node_output_resource_id(task),
        )
        staging_ref = self._table_provider.create_staging_table(
            workflow_run_id=task.workflow_run_id,
            node_run_id=task.node_run_id,
            output_name=output_name,
            schema=schema,
        )
        self._table_provider.insert_rows(staging_ref, rows)
        self._registry.register_staging(staging_ref)
        return self._registry.publish(staging_ref.table_ref_id)


class _NodeValidationError(ValueError):
    pass


def _parse_columns(value: Any) -> list[FieldSchemaModel]:
    if value is None:
        value = ["row_id", "amount"]
    if not isinstance(value, list) or not value:
        raise _NodeValidationError(
            "GenerateTestTableNode config.columns must be a list"
        )
    fields: list[FieldSchemaModel] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            name = item
            data_type = _infer_data_type(name)
            nullable = False
            field_id = name
        elif isinstance(item, dict):
            name_value = item.get("name")
            if not isinstance(name_value, str) or not name_value:
                raise _NodeValidationError("column.name is required")
            name = name_value
            data_type = str(item.get("data_type", _infer_data_type(name)))
            nullable = bool(item.get("nullable", False))
            field_id = str(item.get("field_id", name))
        else:
            raise _NodeValidationError("columns must contain strings or objects")
        fields.append(
            FieldSchemaModel(
                field_id=field_id,
                name=name,
                data_type=data_type,
                nullable=nullable,
                ordinal=index,
            )
        )
    return fields


def _int_config(
    config: dict[str, Any],
    key: str,
    *,
    default: int | None = None,
) -> int:
    value = config.get(key, default)
    if not isinstance(value, int):
        raise _NodeValidationError(f"config.{key} must be an integer")
    if value < 0:
        raise _NodeValidationError(f"config.{key} must be non-negative")
    return value


def _infer_data_type(name: str) -> str:
    lowered = name.lower()
    if lowered in {"id", "row_id", "index"} or lowered.endswith("_id"):
        return "INTEGER"
    if lowered in {"amount", "score", "value", "price"}:
        return "FLOAT"
    return "TEXT"


def _node_output_resource_id(task: NodeTaskModel) -> str:
    return f"{task.workflow_run_id}:{task.node_instance_id}:output"


def _generated_value(
    field: FieldSchemaModel,
    *,
    row_number: int,
    seed: int,
) -> int | float | str:
    data_type = field.data_type.upper()
    if data_type in {"INT", "INTEGER"}:
        return row_number
    if data_type in {"FLOAT", "REAL", "DOUBLE", "NUMBER", "NUMERIC", "DECIMAL"}:
        return float(row_number)
    return f"{field.name}_{seed}_{row_number}"


def _normalize_operator(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise _NodeValidationError("FilterRowsNode config.operator is required")
    operator = value.upper()
    if operator not in {"EQ", "NE", "GT", "GE", "LT", "LE", "CONTAINS", "IS_NULL"}:
        raise _NodeValidationError(f"Unsupported filter operator: {value}")
    return operator


def _row_matches(cell_value: Any, *, operator: str, value: Any) -> bool:
    if operator == "EQ":
        return cell_value == value
    if operator == "NE":
        return cell_value != value
    if operator == "GT":
        return cell_value > value
    if operator == "GE":
        return cell_value >= value
    if operator == "LT":
        return cell_value < value
    if operator == "LE":
        return cell_value <= value
    if operator == "CONTAINS":
        return str(value) in str(cell_value)
    if operator == "IS_NULL":
        return cell_value is None
    return False

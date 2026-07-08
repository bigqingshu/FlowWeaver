from __future__ import annotations

import json
from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    CONDITION_FLAG_NODE_TYPE,
    CONDITIONAL_JUMP_NODE_TYPE,
    JUMP_ANCHOR_NODE_TYPE,
    LOOP_JUDGE_NODE_TYPE,
    LOOP_START_NODE_TYPE,
    SUB_WORKFLOW_NODE_TYPE,
    UNCONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.table_node_common import (
    bool_status as _bool_status,
)
from flowweaver.nodes.table_node_common import (
    is_empty_cell as _is_empty_cell,
)
from flowweaver.nodes.table_node_common import (
    row_matches as _row_matches,
)
from flowweaver.nodes.table_node_common import (
    simple_schema as _simple_schema,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    object_config as _object_config,
)
from flowweaver.nodes.table_node_config import (
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_object_list_config as _optional_object_list_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_list_config as _optional_string_list_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.value_sources import ValueSourceError, parse_value_source
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ConditionFlagNodeHandler:
    node_type = CONDITION_FLAG_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        flag_name = _optional_node_string_config(
            task.config,
            "flag_name",
            default="condition",
            node_type=self.node_type,
        )
        condition_type = _enum_config(
            task.config,
            "condition_type",
            default="row_count",
            allowed={"row_count", "field_exists", "field_value"},
            node_type=self.node_type,
        )
        aggregation = _enum_config(
            task.config,
            "aggregation",
            default="any",
            allowed={"any", "all", "first", "count"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        result, matched_count, details = _condition_flag_result(
            task.config,
            context,
            input_ref=input_ref,
            condition_type=condition_type,
            aggregation=aggregation,
            total_rows=total_rows,
        )
        true_value = task.config.get("true_value", True)
        false_value = task.config.get("false_value", False)
        output_value = true_value if result else false_value
        status_row = {
            "flag_name": flag_name,
            "condition_type": condition_type,
            "aggregation": aggregation,
            "result": _bool_status(result),
            "true_value": _condition_flag_output_text(true_value),
            "false_value": _condition_flag_output_text(false_value),
            "output_value": _condition_flag_output_text(output_value),
            "matched_count": matched_count,
            "total_rows": total_rows,
            "details": _json_text(details),
        }
        status_ref = context.publish_rows(
            task,
            output_name=f"{task.node_instance_id}_output",
            schema=_condition_flag_status_schema(),
            rows=[status_row],
        )
        return [status_ref]


class JumpAnchorNodeHandler:
    node_type = JUMP_ANCHOR_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("JumpAnchorNode does not accept inputs")
        anchor_name = _node_string_config(
            task.config,
            "anchor_name",
            node_type=self.node_type,
        )
        description = _optional_string_config(
            task.config,
            "description",
            node_type=self.node_type,
        )
        allow_multiple_hits = _bool_config(
            task.config,
            "allow_multiple_hits",
            default=False,
        )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="anchor",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=anchor_name,
                action="declare_anchor",
                reason=description,
                details={
                    "anchor_name": anchor_name,
                    "description": description,
                    "allow_multiple_hits": allow_multiple_hits,
                },
            )
        ]


class UnconditionalJumpNodeHandler:
    node_type = UNCONDITIONAL_JUMP_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if len(task.input_refs) > 1:
            raise _NodeValidationError(
                "UnconditionalJumpNode accepts at most one input_ref"
            )
        target_mode = _enum_config(
            task.config,
            "target_mode",
            default="anchor",
            allowed={"anchor", "node"},
            node_type=self.node_type,
        )
        target_anchor = _optional_string_config(
            task.config,
            "target_anchor",
            node_type=self.node_type,
        )
        target_node_id = _optional_string_config(
            task.config,
            "target_node_id",
            node_type=self.node_type,
        )
        reason = _optional_string_config(
            task.config,
            "reason",
            node_type=self.node_type,
        )
        if target_mode == "anchor":
            if not target_anchor.strip():
                raise _NodeValidationError(
                    "UnconditionalJumpNode config.target_anchor is required"
                )
            action = "jump_to_anchor"
            target_node_id = ""
        else:
            if not target_node_id.strip():
                raise _NodeValidationError(
                    "UnconditionalJumpNode config.target_node_id is required"
                )
            action = "jump_to_node"
            target_anchor = ""
        return [
            _publish_control_status(
                context,
                task,
                signal_type="jump",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_node_id=target_node_id.strip(),
                target_anchor=target_anchor.strip(),
                action=action,
                reason=reason,
                details={
                    "target_mode": target_mode,
                    "target_anchor": target_anchor.strip(),
                    "target_node_id": target_node_id.strip(),
                    "reason": reason,
                    "input_ref_id": task.input_refs[0] if task.input_refs else "",
                },
            )
        ]


class ConditionalJumpNodeHandler:
    node_type = CONDITIONAL_JUMP_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        condition_field = _optional_node_string_config(
            task.config,
            "condition_field",
            default="result",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, condition_field) is None:
            raise _NodeValidationError(f"Field does not exist: {condition_field}")
        default_branch = _enum_config(
            task.config,
            "default_branch",
            default="false",
            allowed={"true", "false"},
            node_type=self.node_type,
        )
        rows = context.read_all_rows(input_ref)
        raw_condition = rows[0].get(condition_field) if rows else None
        parsed_condition = _condition_jump_bool(raw_condition)
        if parsed_condition is None:
            selected_branch = default_branch
            condition_result = ""
            signal_status = "matched" if selected_branch == "true" else "not_matched"
            reason = (
                "condition value is missing or unsupported; "
                f"used default_branch={default_branch}"
            )
        else:
            selected_branch = _bool_status(parsed_condition)
            condition_result = selected_branch
            signal_status = "matched" if parsed_condition else "not_matched"
            reason = f"condition result is {selected_branch}"

        target_mode, target_anchor, target_node_id, action = (
            _conditional_jump_target_config(
                task.config,
                branch=selected_branch,
            )
        )
        return [
            _publish_control_status(
                context,
                task,
                signal_type="conditional_jump",
                signal_status=signal_status,
                source_node_id=task.node_instance_id,
                target_node_id=target_node_id,
                target_anchor=target_anchor,
                condition_result=condition_result,
                selected_branch=selected_branch,
                action=action,
                reason=reason,
                details={
                    "condition_field": condition_field,
                    "raw_condition": raw_condition,
                    "parsed_condition": condition_result,
                    "selected_branch": selected_branch,
                    "default_branch": default_branch,
                    "target_mode": target_mode,
                    "target_anchor": target_anchor,
                    "target_node_id": target_node_id,
                    "input_ref_id": input_ref.table_ref_id,
                },
            )
        ]


class LoopStartNodeHandler:
    node_type = LOOP_START_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if len(task.input_refs) > 1:
            raise _NodeValidationError("LoopStartNode accepts at most one input_ref")
        input_ref = context.input_ref(task.input_refs[0]) if task.input_refs else None
        loop_id = _node_string_config(
            task.config,
            "loop_id",
            node_type=self.node_type,
        )
        source_type = _enum_config(
            task.config,
            "source_type",
            default="current_table",
            allowed={"current_table", "named_table", "sqlite"},
            node_type=self.node_type,
        )
        fields = _optional_string_list_config(
            task.config,
            "fields",
            node_type=self.node_type,
        )
        max_loop_count = _positive_int_config(
            task.config,
            "max_loop_count",
            default=1,
            node_type=self.node_type,
        )
        output_current_as_table = _bool_config(
            task.config,
            "output_current_as_table",
            default=True,
        )
        current_table_name = _optional_string_config(
            task.config,
            "current_table_name",
            default="current_loop_item",
            node_type=self.node_type,
        )
        total_items = context.count_rows(input_ref) if input_ref is not None else 0
        planned_iterations = min(total_items, max_loop_count)
        return [
            _publish_control_status(
                context,
                task,
                signal_type="loop_plan",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=loop_id,
                action="declare_loop_plan",
                reason="preview only; no loop scheduling is performed",
                details={
                    "loop_id": loop_id,
                    "source_type": source_type,
                    "fields": fields,
                    "max_loop_count": max_loop_count,
                    "total_items": total_items,
                    "planned_iterations": planned_iterations,
                    "output_current_as_table": output_current_as_table,
                    "current_table_name": current_table_name,
                    "input_ref_id": input_ref.table_ref_id if input_ref else "",
                },
            )
        ]


class LoopJudgeNodeHandler:
    node_type = LOOP_JUDGE_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        loop_id = _node_string_config(
            task.config,
            "loop_id",
            node_type=self.node_type,
        )
        condition_mode = _enum_config(
            task.config,
            "condition_mode",
            default="always_success",
            allowed={"always_success", "row_count", "field_value"},
            node_type=self.node_type,
        )
        on_success = _enum_config(
            task.config,
            "on_success",
            default="continue_loop",
            allowed={"continue_loop", "end_loop"},
            node_type=self.node_type,
        )
        on_fail = _enum_config(
            task.config,
            "on_fail",
            default="end_loop",
            allowed={"continue_loop", "end_loop"},
            node_type=self.node_type,
        )
        total_rows = context.count_rows(input_ref)
        condition_result, matched_count, condition_details = _loop_judge_result(
            task.config,
            context,
            input_ref=input_ref,
            condition_mode=condition_mode,
            total_rows=total_rows,
        )
        selected_action = on_success if condition_result else on_fail
        return [
            _publish_control_status(
                context,
                task,
                signal_type="loop_decision",
                signal_status="matched" if condition_result else "not_matched",
                source_node_id=task.node_instance_id,
                target_anchor=loop_id,
                condition_result=_bool_status(condition_result),
                selected_branch=selected_action,
                action=f"{selected_action}_preview",
                reason=(
                    f"condition result is {_bool_status(condition_result)}; "
                    "preview only; no loop scheduling is performed"
                ),
                details={
                    "loop_id": loop_id,
                    "condition_mode": condition_mode,
                    "matched_count": matched_count,
                    "total_rows": total_rows,
                    "on_success": on_success,
                    "on_fail": on_fail,
                    "selected_action": selected_action,
                    "condition_details": condition_details,
                    "input_ref_id": input_ref.table_ref_id,
                    "result_table_name": _optional_string_config(
                        task.config,
                        "result_table_name",
                        default="loop_result",
                        node_type=self.node_type,
                    ),
                },
            )
        ]


class SubWorkflowNodeHandler:
    node_type = SUB_WORKFLOW_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_refs = [context.input_ref(ref_id) for ref_id in task.input_refs]
        group_name = _node_string_config(
            task.config,
            "group_name",
            node_type=self.node_type,
        )
        subworkflow_ref = _optional_string_config(
            task.config,
            "subworkflow_ref",
            node_type=self.node_type,
        ).strip()
        nodes = _optional_object_list_config(
            task.config,
            "nodes",
            node_type=self.node_type,
        )
        input_source_type = _enum_config(
            task.config,
            "input_source_type",
            default="current_table",
            allowed={"current_table", "named_inputs", "none"},
            node_type=self.node_type,
        )
        input_mapping = _optional_object_list_config(
            task.config,
            "input_mapping",
            node_type=self.node_type,
        )
        input_defaults = _object_config(
            task.config,
            "input_defaults",
            node_type=self.node_type,
        )
        missing_input_policy = _enum_config(
            task.config,
            "missing_input_policy",
            default="error",
            allowed={"error", "skip", "use_default"},
            node_type=self.node_type,
        )
        transit_scope = _enum_config(
            task.config,
            "transit_scope",
            default="isolated",
            allowed={"isolated", "inherited"},
            node_type=self.node_type,
        )
        allow_loop_nodes = _bool_config(
            task.config,
            "allow_loop_nodes",
            default=False,
        )
        main_output_mode = _enum_config(
            task.config,
            "main_output_mode",
            default="status_only",
            allowed={"status_only", "passthrough", "named_outputs"},
            node_type=self.node_type,
        )
        save_to_transit = _bool_config(
            task.config,
            "save_to_transit",
            default=False,
        )
        output_transit_name = _optional_string_config(
            task.config,
            "output_transit_name",
            node_type=self.node_type,
        ).strip()
        if save_to_transit and not output_transit_name:
            raise _NodeValidationError(
                "SubWorkflowNode config.output_transit_name is required"
            )
        blocked_loop_nodes = _subworkflow_loop_node_ids(nodes)
        if blocked_loop_nodes and not allow_loop_nodes:
            raise _NodeValidationError(
                "SubWorkflowNode config.nodes contains loop nodes while "
                "allow_loop_nodes is false: "
                + ", ".join(blocked_loop_nodes)
            )
        input_summaries = [
            {
                "table_ref_id": input_ref.table_ref_id,
                "logical_table_id": input_ref.logical_table_id,
                "role": input_ref.role.value,
                "storage_kind": input_ref.storage_kind.value,
                "field_count": len(input_ref.schema),
            }
            for input_ref in input_refs
        ]
        return [
            _publish_control_status(
                context,
                task,
                signal_type="subworkflow_plan",
                signal_status="planned",
                source_node_id=task.node_instance_id,
                target_anchor=group_name,
                action="declare_subworkflow_plan",
                reason="preview only; no child workflow run is created",
                details={
                    "group_name": group_name,
                    "subworkflow_ref": subworkflow_ref,
                    "node_count": len(nodes),
                    "input_source_type": input_source_type,
                    "input_ref_count": len(input_refs),
                    "input_refs": input_summaries,
                    "input_mapping": input_mapping,
                    "input_defaults": input_defaults,
                    "missing_input_policy": missing_input_policy,
                    "transit_scope": transit_scope,
                    "allow_loop_nodes": allow_loop_nodes,
                    "main_output_mode": main_output_mode,
                    "save_to_transit": save_to_transit,
                    "output_transit_name": output_transit_name,
                },
            )
        ]


def _subworkflow_loop_node_ids(nodes: list[dict[str, Any]]) -> list[str]:
    loop_node_types = {LOOP_START_NODE_TYPE, LOOP_JUDGE_NODE_TYPE}
    blocked: list[str] = []
    for index, node in enumerate(nodes, start=1):
        node_type = node.get("node_type")
        if node_type not in loop_node_types:
            continue
        node_instance_id = node.get("node_instance_id")
        blocked.append(
            node_instance_id.strip()
            if isinstance(node_instance_id, str) and node_instance_id.strip()
            else f"node[{index}]"
        )
    return blocked


def _condition_flag_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    condition_type: str,
    aggregation: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    if condition_type == "row_count":
        return _condition_flag_row_count_result(config, total_rows=total_rows)
    if condition_type == "field_exists":
        return _condition_flag_field_exists_result(
            config,
            input_ref=input_ref,
            total_rows=total_rows,
        )
    if condition_type == "field_value":
        return _condition_flag_field_value_result(
            config,
            context,
            input_ref=input_ref,
            aggregation=aggregation,
            total_rows=total_rows,
        )
    raise _NodeValidationError(
        f"Unsupported ConditionFlagNode condition_type: {condition_type}"
    )


def _condition_flag_row_count_result(
    config: dict[str, Any],
    *,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    operator = _normalize_condition_flag_operator(config.get("operator", "GE"))
    if _condition_flag_operator_requires_value(
        operator
    ) and not _condition_flag_has_value_config(config):
        value = 1
    else:
        value = _condition_flag_value_source(config).resolve({})
    result = _condition_flag_cell_matches(
        total_rows,
        operator=operator,
        value=value,
        case_sensitive=True,
    )
    details = {
        "row_count": total_rows,
        "operator": operator,
        "value": value,
    }
    return result, total_rows if result else 0, details


def _condition_flag_field_exists_result(
    config: dict[str, Any],
    *,
    input_ref: TableRefModel,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    field = _node_string_config(
        config,
        "field",
        node_type=CONDITION_FLAG_NODE_TYPE,
    )
    exists = find_field(input_ref.schema, field) is not None
    return (
        exists,
        total_rows if exists else 0,
        {
            "field": field,
            "exists": exists,
        },
    )


def _condition_flag_field_value_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    aggregation: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    field = _node_string_config(
        config,
        "field",
        node_type=CONDITION_FLAG_NODE_TYPE,
    )
    if find_field(input_ref.schema, field) is None:
        raise _NodeValidationError(f"Field does not exist: {field}")
    operator = _normalize_condition_flag_operator(config.get("operator"))
    if _condition_flag_operator_requires_value(operator):
        _condition_flag_require_value_config(config)
    value_source = _condition_flag_value_source(config)
    if (
        value_source.field is not None
        and find_field(input_ref.schema, value_source.field) is None
    ):
        raise _NodeValidationError(f"Field does not exist: {value_source.field}")
    case_sensitive = _bool_config(config, "case_sensitive", default=True)
    matched_count = 0
    first_match: bool | None = None
    for rows in context.iter_row_batches(input_ref):
        for row in rows:
            try:
                value = value_source.resolve(row)
            except ValueSourceError as exc:
                raise _NodeValidationError(str(exc)) from exc
            matched = _condition_flag_cell_matches(
                row.get(field),
                operator=operator,
                value=value,
                case_sensitive=case_sensitive,
            )
            if aggregation == "first":
                first_match = matched
                matched_count = 1 if matched else 0
                break
            if matched:
                matched_count += 1
        if aggregation == "first" and first_match is not None:
            break
    if aggregation == "any":
        result = matched_count > 0
    elif aggregation == "all":
        result = total_rows > 0 and matched_count == total_rows
    elif aggregation == "first":
        result = bool(first_match)
    else:
        result = matched_count > 0
    details = {
        "field": field,
        "operator": operator,
        "value_source": (
            "field"
            if value_source.field is not None
            else "literal"
        ),
        "value_field": value_source.field or "",
        "case_sensitive": case_sensitive,
    }
    return result, matched_count, details


def _condition_flag_value_source(config: dict[str, Any]):
    raw_value_source = config.get("value_source")
    if raw_value_source == "field":
        value_field = _node_string_config(
            config,
            "value_field",
            node_type=CONDITION_FLAG_NODE_TYPE,
        )
        raw_value_source = {
            "mode": "row_field",
            "field": value_field,
        }
    elif isinstance(raw_value_source, dict):
        raw_value_source = dict(raw_value_source)
        if raw_value_source.get("mode") == "field":
            raw_value_source["mode"] = "row_field"
    elif config.get("value_field") is not None:
        value_field = _node_string_config(
            config,
            "value_field",
            node_type=CONDITION_FLAG_NODE_TYPE,
        )
        raw_value_source = {
            "mode": "row_field",
            "field": value_field,
        }
    else:
        raw_value_source = config.get("value")
    try:
        return parse_value_source(raw_value_source)
    except ValueSourceError as exc:
        raise _NodeValidationError(str(exc)) from exc


def _condition_flag_require_value_config(config: dict[str, Any]) -> None:
    if not _condition_flag_has_value_config(config):
        raise _NodeValidationError("ConditionFlagNode config.value is required")


def _condition_flag_has_value_config(config: dict[str, Any]) -> bool:
    return (
        "value" in config
        or "value_source" in config
        or "value_field" in config
    )


def _normalize_condition_flag_operator(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _NodeValidationError("ConditionFlagNode config.operator is required")
    operator = value.strip().upper()
    if operator not in {
        "EQ",
        "NE",
        "GT",
        "GE",
        "LT",
        "LE",
        "CONTAINS",
        "IS_NULL",
        "IS_EMPTY",
    }:
        raise _NodeValidationError(
            f"Unsupported ConditionFlagNode operator: {value}"
        )
    return operator


def _condition_flag_operator_requires_value(operator: str) -> bool:
    return operator not in {"IS_NULL", "IS_EMPTY"}


def _condition_flag_cell_matches(
    cell_value: Any,
    *,
    operator: str,
    value: Any,
    case_sensitive: bool,
) -> bool:
    if operator == "IS_EMPTY":
        return _is_empty_cell(cell_value)
    if operator == "IS_NULL":
        return cell_value is None
    if not case_sensitive and operator in {"EQ", "NE", "CONTAINS"}:
        cell_text = "" if cell_value is None else str(cell_value)
        value_text = "" if value is None else str(value)
        candidate = cell_text.lower()
        expected = value_text.lower()
        if operator == "EQ":
            return candidate == expected
        if operator == "NE":
            return candidate != expected
        return expected in candidate
    try:
        return _row_matches(cell_value, operator=operator, value=value)
    except TypeError as exc:
        raise _NodeValidationError(
            "ConditionFlagNode cannot compare values with operator "
            f"{operator}"
        ) from exc


def _condition_flag_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("flag_name", "TEXT", False),
            ("condition_type", "TEXT", False),
            ("aggregation", "TEXT", False),
            ("result", "TEXT", False),
            ("true_value", "TEXT", False),
            ("false_value", "TEXT", False),
            ("output_value", "TEXT", False),
            ("matched_count", "INTEGER", False),
            ("total_rows", "INTEGER", False),
            ("details", "TEXT", False),
        ]
    )


def _control_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("signal_type", "TEXT", False),
            ("signal_status", "TEXT", False),
            ("source_node_id", "TEXT", False),
            ("target_node_id", "TEXT", False),
            ("target_anchor", "TEXT", False),
            ("condition_result", "TEXT", False),
            ("selected_branch", "TEXT", False),
            ("action", "TEXT", False),
            ("actual_control", "TEXT", False),
            ("reason", "TEXT", False),
            ("details", "TEXT", False),
        ]
    )


def _publish_control_status(
    context: BuiltinTableNodeContext,
    task: NodeTaskModel,
    *,
    signal_type: str,
    signal_status: str,
    source_node_id: str,
    action: str,
    target_node_id: str = "",
    target_anchor: str = "",
    condition_result: str = "",
    selected_branch: str = "",
    reason: str = "",
    details: dict[str, Any] | None = None,
) -> TableRefModel:
    row = {
        "signal_type": signal_type,
        "signal_status": signal_status,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "target_anchor": target_anchor,
        "condition_result": condition_result,
        "selected_branch": selected_branch,
        "action": action,
        "actual_control": _bool_status(False),
        "reason": reason,
        "details": _json_text(details or {}),
    }
    return context.publish_rows(
        task,
        output_name=f"{task.node_instance_id}_output",
        schema=_control_status_schema(),
        rows=[row],
    )


def _conditional_jump_target_config(
    config: dict[str, Any],
    *,
    branch: str,
) -> tuple[str, str, str, str]:
    prefix = "true" if branch == "true" else "false"
    target_mode = _enum_config(
        config,
        f"{prefix}_target_mode",
        default="anchor",
        allowed={"anchor", "node"},
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    target_anchor = _optional_string_config(
        config,
        f"{prefix}_target_anchor",
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    target_node_id = _optional_string_config(
        config,
        f"{prefix}_target_node_id",
        node_type=CONDITIONAL_JUMP_NODE_TYPE,
    )
    if target_mode == "anchor":
        if not target_anchor.strip():
            raise _NodeValidationError(
                f"ConditionalJumpNode config.{prefix}_target_anchor is required"
            )
        return target_mode, target_anchor.strip(), "", "jump_to_anchor"
    if not target_node_id.strip():
        raise _NodeValidationError(
            f"ConditionalJumpNode config.{prefix}_target_node_id is required"
        )
    return target_mode, "", target_node_id.strip(), "jump_to_node"


def _condition_jump_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None


def _loop_judge_result(
    config: dict[str, Any],
    context: BuiltinTableNodeContext,
    *,
    input_ref: TableRefModel,
    condition_mode: str,
    total_rows: int,
) -> tuple[bool, int, dict[str, Any]]:
    if condition_mode == "always_success":
        return True, total_rows, {"condition_mode": condition_mode}
    if condition_mode == "row_count":
        judge_config = {
            "operator": config.get("condition_op", "GE"),
            "value": config.get("condition_value", 1),
        }
        result, matched_count, details = _condition_flag_result(
            judge_config,
            context,
            input_ref=input_ref,
            condition_type="row_count",
            aggregation="any",
            total_rows=total_rows,
        )
        return result, matched_count, details | {"condition_mode": condition_mode}
    if condition_mode == "field_value":
        condition_field = _node_string_config(
            config,
            "condition_field",
            node_type=LOOP_JUDGE_NODE_TYPE,
        )
        if find_field(input_ref.schema, condition_field) is None:
            raise _NodeValidationError(f"Field does not exist: {condition_field}")
        judge_config = {
            "field": condition_field,
            "operator": config.get("condition_op", "EQ"),
            "aggregation": "any",
        }
        if "condition_value_source" in config:
            judge_config["value_source"] = config["condition_value_source"]
        elif "condition_value_field" in config:
            judge_config["value_field"] = config["condition_value_field"]
        else:
            judge_config["value"] = config.get("condition_value")
        result, matched_count, details = _condition_flag_result(
            judge_config,
            context,
            input_ref=input_ref,
            condition_type="field_value",
            aggregation="any",
            total_rows=total_rows,
        )
        return result, matched_count, details | {"condition_mode": condition_mode}
    raise _NodeValidationError(
        f"Unsupported LoopJudgeNode condition_mode: {condition_mode}"
    )


def _condition_flag_output_text(value: Any) -> str:
    if isinstance(value, bool):
        return _bool_status(value)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return _json_text(value)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)



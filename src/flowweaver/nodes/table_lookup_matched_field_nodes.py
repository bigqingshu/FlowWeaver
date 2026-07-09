from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import (
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
)
from flowweaver.nodes.table_lookup_matched_field_helpers import (
    lookup_matched_field_index as _lookup_matched_field_index,
)
from flowweaver.nodes.table_lookup_matched_field_helpers import (
    lookup_matched_output_fields as _lookup_matched_output_fields,
)
from flowweaver.nodes.table_lookup_matched_field_helpers import (
    lookup_matched_output_schema as _lookup_matched_output_schema,
)
from flowweaver.nodes.table_lookup_matched_field_helpers import (
    lookup_matched_select_match as _lookup_matched_select_match,
)
from flowweaver.nodes.table_lookup_matched_field_helpers import (
    lookup_matched_values as _lookup_matched_values,
)
from flowweaver.nodes.table_node_config import (
    enum_config as _enum_config,
)
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_config import (
    string_list_config as _string_list_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_ops import (
    find_field,
    has_field,
)
from flowweaver.protocols.enums import TableStorageKind
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class LookupMatchedFieldNameNodeHandler:
    node_type = LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        allowed_storage_kinds = (
            TableStorageKind.RUNTIME_SQL,
            TableStorageKind.MEMORY,
        )
        if task.input_slot_bindings:
            main_ref = context.require_input_slot(
                task,
                "in",
                node_type=self.node_type,
                allowed_storage_kinds=allowed_storage_kinds,
            )
            lookup_ref = context.require_input_slot(
                task,
                "lookup",
                node_type=self.node_type,
                allowed_storage_kinds=allowed_storage_kinds,
            )
        else:
            if len(task.input_refs) != 2:
                raise _NodeValidationError(
                    "LookupMatchedFieldNameNode requires main and lookup input_refs"
                )
            main_ref = context.input_ref(task.input_refs[0])
            lookup_ref = context.input_ref(task.input_refs[1])
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        if find_field(main_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        lookup_fields = _string_list_config(
            task.config,
            "lookup_fields",
            node_type=self.node_type,
        )
        missing_lookup_fields = [
            field_name
            for field_name in lookup_fields
            if not has_field(lookup_ref.schema, field_name)
        ]
        if missing_lookup_fields:
            raise _NodeValidationError(
                f"Fields do not exist: {', '.join(missing_lookup_fields)}"
            )
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="equals",
            allowed={"equals"},
            node_type=self.node_type,
        )
        multi_match_policy = _enum_config(
            task.config,
            "multi_match_policy",
            default="first",
            allowed={"first", "last", "error"},
            node_type=self.node_type,
        )
        output_fields = _lookup_matched_output_fields(task.config)
        output_schema = _lookup_matched_output_schema(main_ref.schema, output_fields)
        no_match_value = task.config.get("no_match_value", "")
        lookup_index = _lookup_matched_field_index(
            context,
            lookup_ref=lookup_ref,
            lookup_fields=lookup_fields,
            match_mode=match_mode,
        )

        def output_batches():
            for rows in context.iter_row_batches(main_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    matches = lookup_index.get(row.get(source_field), [])
                    if len(matches) > 1 and multi_match_policy == "error":
                        raise _NodeValidationError(
                            "LookupMatchedFieldNameNode found multiple matches"
                        )
                    match = _lookup_matched_select_match(
                        matches,
                        multi_match_policy=multi_match_policy,
                    )
                    output_rows.append(
                        dict(row)
                        | _lookup_matched_values(
                            match,
                            match_count=len(matches),
                            output_fields=output_fields,
                            no_match_value=no_match_value,
                        )
                    )
                yield output_rows

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=output_schema,
                row_batches=output_batches(),
            )
        ]

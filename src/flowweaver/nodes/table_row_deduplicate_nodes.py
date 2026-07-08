from __future__ import annotations

from typing import Any

from flowweaver.nodes.builtin_table_node_types import DEDUPLICATE_ROWS_NODE_TYPE
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import primary_input_ref as _primary_input_ref
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_groups as _deduplicate_groups,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_key as _deduplicate_key,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_key_fields as _deduplicate_key_fields,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_marker_fields as _deduplicate_marker_fields,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_marker_values as _deduplicate_marker_values,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_occurrence_index as _deduplicate_occurrence_index,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_output_schema as _deduplicate_output_schema,
)
from flowweaver.nodes.table_row_deduplicate_helpers import (
    deduplicate_should_keep as _deduplicate_should_keep,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class DeduplicateRowsNodeHandler:
    node_type = DEDUPLICATE_ROWS_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = _primary_input_ref(
            task,
            context,
            node_type=self.node_type,
        )
        key_fields = _deduplicate_key_fields(task.config, input_ref)
        trim = _bool_config(task.config, "trim", default=False)
        ignore_case = _bool_config(task.config, "ignore_case", default=False)
        empty_key_policy = _enum_config(
            task.config,
            "empty_key_policy",
            default="include",
            allowed={"include", "skip"},
            node_type=self.node_type,
        )
        keep_policy = _enum_config(
            task.config,
            "keep_policy",
            default="first",
            allowed={"first", "last", "all"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="dedupe",
            allowed={"dedupe", "mark"},
            node_type=self.node_type,
        )
        add_marker_columns = _bool_config(
            task.config,
            "add_marker_columns",
            default=output_mode == "mark",
        )
        if output_mode == "mark" and not add_marker_columns:
            raise _NodeValidationError(
                "DeduplicateRowsNode output_mode=mark requires marker columns"
            )
        marker_fields = _deduplicate_marker_fields(task.config)
        output_schema = (
            _deduplicate_output_schema(input_ref.schema, marker_fields)
            if add_marker_columns
            else input_ref.schema
        )
        groups = _deduplicate_groups(
            context,
            input_ref=input_ref,
            key_fields=key_fields,
            trim=trim,
            ignore_case=ignore_case,
            empty_key_policy=empty_key_policy,
        )

        def output_batches():
            row_number = 1
            occurrence_counts: dict[tuple[Any, ...], int] = {}
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    key = _deduplicate_key(
                        row,
                        key_fields=key_fields,
                        trim=trim,
                        ignore_case=ignore_case,
                        empty_key_policy=empty_key_policy,
                    )
                    occurrence_index = _deduplicate_occurrence_index(
                        occurrence_counts,
                        key,
                    )
                    keep_row = _deduplicate_should_keep(
                        row_number,
                        key=key,
                        groups=groups,
                        keep_policy=keep_policy,
                    )
                    if output_mode == "mark" or keep_row:
                        output_row = dict(row)
                        if add_marker_columns:
                            output_row |= _deduplicate_marker_values(
                                key=key,
                                groups=groups,
                                occurrence_index=occurrence_index,
                                keep_row=keep_row,
                                marker_fields=marker_fields,
                            )
                        output_rows.append(output_row)
                    row_number += 1
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )



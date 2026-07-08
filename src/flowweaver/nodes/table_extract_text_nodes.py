from __future__ import annotations

import re
from typing import Any

from flowweaver.nodes.builtin_table_node_types import EXTRACT_TEXT_NODE_TYPE
from flowweaver.nodes.table_extract_text_helpers import SKIP_ROW as _SKIP_ROW
from flowweaver.nodes.table_extract_text_helpers import (
    extract_text_output_field as _extract_text_output_field,
)
from flowweaver.nodes.table_extract_text_helpers import (
    extract_text_output_schema as _extract_text_output_schema,
)
from flowweaver.nodes.table_extract_text_helpers import (
    extract_text_rule_fallback_key as _extract_text_rule_fallback_key,
)
from flowweaver.nodes.table_extract_text_helpers import (
    extract_text_unmatched_value as _extract_text_unmatched_value,
)
from flowweaver.nodes.table_extract_text_helpers import (
    extract_text_value as _extract_text_value,
)
from flowweaver.nodes.table_node_config import bool_config as _bool_config
from flowweaver.nodes.table_node_config import enum_config as _enum_config
from flowweaver.nodes.table_node_config import (
    node_string_config as _node_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    primary_input_ref as _primary_input_ref,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.nodes.table_ops import find_field
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ExtractTextNodeHandler:
    node_type = EXTRACT_TEXT_NODE_TYPE

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
        source_field = _node_string_config(
            task.config,
            "source_field",
            node_type=self.node_type,
        )
        if find_field(input_ref.schema, source_field) is None:
            raise _NodeValidationError(f"Field does not exist: {source_field}")
        method = _enum_config(
            task.config,
            "method",
            default="regex",
            allowed={"regex", "position", "left", "right", "delimiter", "between"},
            node_type=self.node_type,
        )
        output_mode = _enum_config(
            task.config,
            "output_mode",
            default="new_field",
            allowed={"new_field", "overwrite_source", "overwrite"},
            node_type=self.node_type,
        )
        output_field = _extract_text_output_field(
            task.config,
            input_ref=input_ref,
            source_field=source_field,
            output_mode=output_mode,
        )
        output_schema = _extract_text_output_schema(
            input_ref.schema,
            output_field=output_field,
            output_mode=output_mode,
        )
        strip_result = _bool_config(task.config, "strip_result", default=False)
        unmatched_mode = _enum_config(
            task.config,
            "unmatched_mode",
            default="empty",
            allowed={"empty", "keep_original", "fixed", "skip_row"},
            node_type=self.node_type,
        )
        rule_source = _value_source_config(
            task.config,
            "rule_value_source",
            fallback_key=_extract_text_rule_fallback_key(method),
        )
        unmatched_source = _value_source_config(
            task.config,
            "unmatched_value_source",
            fallback_key="unmatched_value",
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        extracted = _extract_text_value(
                            row.get(source_field),
                            row=row,
                            config=task.config,
                            method=method,
                            rule_source=rule_source,
                            strip_result=strip_result,
                        )
                        if extracted is None:
                            extracted = _extract_text_unmatched_value(
                                row,
                                source_value=row.get(source_field),
                                unmatched_mode=unmatched_mode,
                                unmatched_source=unmatched_source,
                            )
                        if extracted is _SKIP_ROW:
                            continue
                    except (ValueSourceError, re.error, IndexError) as exc:
                        raise _NodeValidationError(str(exc)) from exc
                    output_rows.append(dict(row) | {output_field: extracted})
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=output_schema,
            row_batches=output_batches(),
        )


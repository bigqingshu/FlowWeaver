from __future__ import annotations

import re
from typing import Any

from flowweaver.nodes.builtin_table_node_types import REPLACE_TEXT_NODE_TYPE
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
    non_negative_int_config as _non_negative_int_config,
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
from flowweaver.nodes.table_ops import has_field
from flowweaver.nodes.table_replace_text_helpers import (
    replace_text_value as _replace_text_value,
)
from flowweaver.nodes.table_value_source_config import (
    value_source_config as _value_source_config,
)
from flowweaver.nodes.value_sources import ValueSourceError
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ReplaceTextNodeHandler:
    node_type = REPLACE_TEXT_NODE_TYPE

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
        target_field = _node_string_config(
            task.config,
            "target_field",
            node_type=self.node_type,
        )
        if not has_field(input_ref.schema, target_field):
            raise _NodeValidationError(f"Field does not exist: {target_field}")
        match_mode = _enum_config(
            task.config,
            "match_mode",
            default="contains",
            allowed={
                "contains",
                "equals",
                "starts_with",
                "ends_with",
                "regex",
                "is_empty",
                "is_not_empty",
            },
            node_type=self.node_type,
        )
        replace_mode = _enum_config(
            task.config,
            "replace_mode",
            default="partial",
            allowed={"partial", "whole_cell"},
            node_type=self.node_type,
        )
        case_sensitive = _bool_config(
            task.config,
            "case_sensitive",
            default=True,
        )
        replace_count = _non_negative_int_config(
            task.config,
            "replace_count",
            default=0,
            node_type=self.node_type,
        )
        skip_empty_match_value = _bool_config(
            task.config,
            "skip_empty_match_value",
            default=True,
        )
        match_source = _value_source_config(
            task.config,
            "match_value_source",
            fallback_key="match_value",
        )
        replace_source = _value_source_config(
            task.config,
            "replace_value_source",
            fallback_key="replace_value",
        )

        def output_batches():
            for rows in context.iter_row_batches(input_ref):
                output_rows: list[dict[str, Any]] = []
                for row in rows:
                    try:
                        output_rows.append(
                            row | {
                                target_field: _replace_text_value(
                                    row.get(target_field),
                                    row=row,
                                    match_mode=match_mode,
                                    match_source=match_source,
                                    replace_source=replace_source,
                                    replace_mode=replace_mode,
                                    case_sensitive=case_sensitive,
                                    replace_count=replace_count,
                                    skip_empty_match_value=skip_empty_match_value,
                                )
                            }
                        )
                    except (ValueSourceError, re.error) as exc:
                        raise _NodeValidationError(str(exc)) from exc
                yield output_rows

        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=input_ref.schema,
            row_batches=output_batches(),
        )

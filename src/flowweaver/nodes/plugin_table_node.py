from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import PLUGIN_NODE_TYPE
from flowweaver.nodes.plugin_manifest_validation import build_plugin_status_row
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
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


class PluginNodeHandler:
    node_type = PLUGIN_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        plugin_id = _node_string_config(
            task.config,
            "plugin_id",
            node_type=self.node_type,
        )
        plugin_version = _optional_string_config(
            task.config,
            "plugin_version",
            node_type=self.node_type,
        )
        params = _object_config(task.config, "params", node_type=self.node_type)
        input_bindings = _object_config(
            task.config,
            "input_bindings",
            node_type=self.node_type,
        )
        output_bindings = _object_config(
            task.config,
            "output_bindings",
            node_type=self.node_type,
        )
        plugin_manifest = _object_config(
            task.config,
            "plugin_manifest",
            node_type=self.node_type,
        )
        execution_mode = _enum_config(
            task.config,
            "execution_mode",
            default="external_process",
            allowed={"in_process", "external_process"},
            node_type=self.node_type,
        )
        allow_external_actions = _bool_config(
            task.config,
            "allow_external_actions",
            default=False,
        )
        enable_execute = _bool_config(
            task.config,
            "enable_execute",
            default=False,
        )
        status_row = build_plugin_status_row(
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            plugin_manifest=plugin_manifest,
            params=params,
            input_bindings=input_bindings,
            output_bindings=output_bindings,
            input_ref_count=len(task.input_refs),
            execution_mode=execution_mode,
            allow_external_actions=allow_external_actions,
            enable_execute=enable_execute,
        )
        return [
            context.publish_rows(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_plugin_status_schema(),
                rows=[status_row],
            )
        ]


def _plugin_status_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("status", "TEXT", False),
            ("plugin_id", "TEXT", False),
            ("plugin_version", "TEXT", False),
            ("manifest_status", "TEXT", False),
            ("manifest_plugin_id", "TEXT", False),
            ("manifest_plugin_version", "TEXT", False),
            ("execution_mode", "TEXT", False),
            ("input_ref_count", "INTEGER", False),
            ("param_count", "INTEGER", False),
            ("input_binding_count", "INTEGER", False),
            ("output_binding_count", "INTEGER", False),
            ("plugin_found", "TEXT", False),
            ("validation_status", "TEXT", False),
            ("validation_errors", "TEXT", False),
            ("allow_external_actions", "TEXT", False),
            ("enable_execute", "TEXT", False),
            ("external_actions_declared", "TEXT", False),
            ("execution_ready", "TEXT", False),
            ("actual_execute", "TEXT", False),
            ("skipped_reason", "TEXT", False),
        ]
    )



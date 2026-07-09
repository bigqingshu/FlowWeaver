from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import BATCH_RENAME_FILES_NODE_TYPE
from flowweaver.nodes.table_batch_rename_files_helpers import (
    batch_rename_output_batches as _batch_rename_output_batches,
)
from flowweaver.nodes.table_batch_rename_files_helpers import (
    batch_rename_status_schema as _batch_rename_status_schema,
)
from flowweaver.nodes.table_node_common import (
    require_fields as _require_fields,
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
    optional_node_string_config as _optional_node_string_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class BatchRenameFilesNodeHandler:
    node_type = BATCH_RENAME_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        input_ref = context.require_single_input_ref(
            task,
            node_type=self.node_type,
        )
        path_field = _node_string_config(
            task.config,
            "path_field",
            node_type=self.node_type,
        )
        new_name_field = _node_string_config(
            task.config,
            "new_name_field",
            node_type=self.node_type,
        )
        _require_fields(input_ref.schema, [path_field, new_name_field])
        name_value_type = _enum_config(
            task.config,
            "name_value_type",
            default="file_name",
            allowed={"file_name", "full_path"},
            node_type=self.node_type,
        )
        new_path_field = _optional_node_string_config(
            task.config,
            "new_path_field",
            default="new_path",
            node_type=self.node_type,
        )
        status_field = _optional_node_string_config(
            task.config,
            "status_field",
            default="rename_status",
            node_type=self.node_type,
        )
        if new_path_field == status_field:
            raise _NodeValidationError(
                "BatchRenameFilesNode new_path_field and status_field must differ"
            )
        auto_append_ext = _bool_config(task.config, "auto_append_ext", default=True)
        allow_dirs = _bool_config(task.config, "allow_dirs", default=False)
        create_target_dirs = _bool_config(
            task.config,
            "create_target_dirs",
            default=False,
        )
        conflict_mode = _enum_config(
            task.config,
            "conflict_mode",
            default="error",
            allowed={"error", "skip", "overwrite", "append_number"},
            node_type=self.node_type,
        )
        actual_rename = _bool_config(task.config, "actual_rename", default=False)
        write_log = _bool_config(task.config, "write_log", default=False)
        log_path = _optional_string_config(
            task.config,
            "log_path",
            node_type=self.node_type,
        )

        return [
            context.publish_row_batches(
                task,
                output_name=f"{task.node_instance_id}_output",
                schema=_batch_rename_status_schema(
                    new_path_field=new_path_field,
                    status_field=status_field,
                ),
                row_batches=_batch_rename_output_batches(
                    context,
                    input_ref,
                    path_field=path_field,
                    new_name_field=new_name_field,
                    name_value_type=name_value_type,
                    new_path_field=new_path_field,
                    status_field=status_field,
                    auto_append_ext=auto_append_ext,
                    allow_dirs=allow_dirs,
                    create_target_dirs=create_target_dirs,
                    conflict_mode=conflict_mode,
                    actual_rename=actual_rename,
                    write_log=write_log,
                    log_path=log_path,
                ),
            )
        ]




from __future__ import annotations

from flowweaver.nodes.builtin_table_node_types import LIST_FILES_NODE_TYPE
from flowweaver.nodes.table_list_files_config import (
    list_files_directory_config as _list_files_directory_config,
)
from flowweaver.nodes.table_list_files_config import (
    list_files_extensions_config as _list_files_extensions_config,
)
from flowweaver.nodes.table_list_files_rows import (
    list_file_rows as _list_file_rows,
)
from flowweaver.nodes.table_list_files_schema import (
    list_files_schema as _list_files_schema,
)
from flowweaver.nodes.table_node_config import (
    bool_config as _bool_config,
)
from flowweaver.nodes.table_node_config import (
    optional_string_config as _optional_string_config,
)
from flowweaver.nodes.table_node_config import (
    positive_int_config as _positive_int_config,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeContext,
    BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_node_io import (
    publish_primary_table_output as _publish_primary_table_output,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import TableRefModel

_NodeValidationError = BuiltinTableNodeValidationError


class ListFilesNodeHandler:
    node_type = LIST_FILES_NODE_TYPE

    def execute(
        self,
        task: NodeTaskModel,
        context: BuiltinTableNodeContext,
    ) -> list[TableRefModel]:
        if task.input_refs:
            raise _NodeValidationError("ListFilesNode does not accept inputs")
        directory = _list_files_directory_config(task.config)
        recursive = _bool_config(task.config, "recursive", default=False)
        include_files = _bool_config(task.config, "include_files", default=True)
        include_dirs = _bool_config(task.config, "include_dirs", default=False)
        if not include_files and not include_dirs:
            raise _NodeValidationError(
                "ListFilesNode must include files or directories"
            )
        include_hidden = _bool_config(
            task.config,
            "include_hidden",
            default=False,
        )
        extensions = _list_files_extensions_config(task.config)
        name_contains = _optional_string_config(
            task.config,
            "name_contains",
            node_type=self.node_type,
        )
        glob_pattern = _optional_string_config(
            task.config,
            "glob_pattern",
            default="*",
            node_type=self.node_type,
        )
        if not glob_pattern.strip():
            raise _NodeValidationError("ListFilesNode config.glob_pattern is required")
        max_files = _positive_int_config(
            task.config,
            "max_files",
            default=10_000,
            node_type=self.node_type,
        )
        rows = _list_file_rows(
            directory,
            recursive=recursive,
            include_files=include_files,
            include_dirs=include_dirs,
            include_hidden=include_hidden,
            extensions=extensions,
            name_contains=name_contains,
            glob_pattern=glob_pattern,
            max_files=max_files,
        )
        return _publish_primary_table_output(
            task,
            context,
            node_type=self.node_type,
            schema=_list_files_schema(),
            row_batches=(rows,),
        )

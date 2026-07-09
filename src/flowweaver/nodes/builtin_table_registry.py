from __future__ import annotations

from flowweaver.nodes.file_table_nodes import (
    BatchRenameFilesNodeHandler,
    ListFilesNodeHandler,
)
from flowweaver.nodes.plugin_table_node import PluginNodeHandler
from flowweaver.nodes.sql_mapping_table_node import SqlMappingNodeHandler
from flowweaver.nodes.table_control_nodes import (
    ConditionalJumpNodeHandler,
    ConditionFlagNodeHandler,
    JumpAnchorNodeHandler,
    LoopJudgeNodeHandler,
    LoopStartNodeHandler,
    SubWorkflowNodeHandler,
    UnconditionalJumpNodeHandler,
)
from flowweaver.nodes.table_node_handlers import BuiltinTableNodeHandlerRegistry
from flowweaver.nodes.table_transform_nodes import (
    AddColumnsNodeHandler,
    AddCurrentDateTimeColumnNodeHandler,
    AdvancedFilterRowsNodeHandler,
    CopyColumnNodeHandler,
    CopyRowsNodeHandler,
    DeduplicateRowsNodeHandler,
    DeleteColumnsNodeHandler,
    DeleteRowsNodeHandler,
    ExtractTextNodeHandler,
    FillCellsNodeHandler,
    FillRangeNodeHandler,
    FillSequenceNodeHandler,
    FilterRowsNodeHandler,
    GenerateTestTableNodeHandler,
    LookupMatchedFieldNameNodeHandler,
    MergeColumnsNodeHandler,
    NumericColumnOperationNodeHandler,
    ParseDateTimeNodeHandler,
    RenameColumnsNodeHandler,
    ReorderColumnsNodeHandler,
    ReplaceTextNodeHandler,
    UnpivotRowsNodeHandler,
)
from flowweaver.nodes.table_write_nodes import (
    SaveMemoryTableNodeHandler,
    SaveRunTableNodeHandler,
    WriteBackTableNodeHandler,
    WriteSelectedColumnsNodeHandler,
)


def table_node_types() -> tuple[str, ...]:
    return create_builtin_table_node_handler_registry().node_types()


def is_table_node_type(node_type: str) -> bool:
    return node_type in table_node_types()


def create_builtin_table_node_handler_registry() -> BuiltinTableNodeHandlerRegistry:
    return BuiltinTableNodeHandlerRegistry(
        handlers=(
            GenerateTestTableNodeHandler(),
            FilterRowsNodeHandler(),
            AddColumnsNodeHandler(),
            DeleteColumnsNodeHandler(),
            CopyColumnNodeHandler(),
            ReorderColumnsNodeHandler(),
            RenameColumnsNodeHandler(),
            FillCellsNodeHandler(),
            FillRangeNodeHandler(),
            FillSequenceNodeHandler(),
            ReplaceTextNodeHandler(),
            DeleteRowsNodeHandler(),
            CopyRowsNodeHandler(),
            UnpivotRowsNodeHandler(),
            DeduplicateRowsNodeHandler(),
            AdvancedFilterRowsNodeHandler(),
            ExtractTextNodeHandler(),
            LookupMatchedFieldNameNodeHandler(),
            MergeColumnsNodeHandler(),
            NumericColumnOperationNodeHandler(),
            AddCurrentDateTimeColumnNodeHandler(),
            ParseDateTimeNodeHandler(),
            ConditionFlagNodeHandler(),
            JumpAnchorNodeHandler(),
            UnconditionalJumpNodeHandler(),
            ConditionalJumpNodeHandler(),
            LoopStartNodeHandler(),
            LoopJudgeNodeHandler(),
            SubWorkflowNodeHandler(),
            SaveMemoryTableNodeHandler(),
            SaveRunTableNodeHandler(),
            WriteSelectedColumnsNodeHandler(),
            WriteBackTableNodeHandler(),
            ListFilesNodeHandler(),
            BatchRenameFilesNodeHandler(),
            PluginNodeHandler(),
            SqlMappingNodeHandler(),
        )
    )

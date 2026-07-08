from __future__ import annotations

from flowweaver.nodes.builtin_sql import (
    SQL_MAPPING_NODE_TYPE as SQL_MAPPING_NODE_TYPE,
)
from flowweaver.nodes.builtin_sql import (
    SqlMappingTaskConfig as SqlMappingTaskConfig,
)
from flowweaver.nodes.builtin_table_node_types import (
    ADD_COLUMNS_NODE_TYPE as ADD_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE as ADD_CURRENT_DATETIME_COLUMN_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    ADVANCED_FILTER_ROWS_NODE_TYPE as ADVANCED_FILTER_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    BATCH_RENAME_FILES_NODE_TYPE as BATCH_RENAME_FILES_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    CONDITION_FLAG_NODE_TYPE as CONDITION_FLAG_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    CONDITIONAL_JUMP_NODE_TYPE as CONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    COPY_COLUMN_NODE_TYPE as COPY_COLUMN_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    COPY_ROWS_NODE_TYPE as COPY_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    DEDUPLICATE_ROWS_NODE_TYPE as DEDUPLICATE_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    DELETE_COLUMNS_NODE_TYPE as DELETE_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    DELETE_ROWS_NODE_TYPE as DELETE_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    EXTRACT_TEXT_NODE_TYPE as EXTRACT_TEXT_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    FILL_CELLS_NODE_TYPE as FILL_CELLS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    FILL_RANGE_NODE_TYPE as FILL_RANGE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    FILL_SEQUENCE_NODE_TYPE as FILL_SEQUENCE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    FILTER_ROWS_NODE_TYPE as FILTER_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    GENERATE_TEST_TABLE_NODE_TYPE as GENERATE_TEST_TABLE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    JUMP_ANCHOR_NODE_TYPE as JUMP_ANCHOR_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    LIST_FILES_NODE_TYPE as LIST_FILES_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE as LOOKUP_MATCHED_FIELD_NAME_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    LOOP_JUDGE_NODE_TYPE as LOOP_JUDGE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    LOOP_START_NODE_TYPE as LOOP_START_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    MERGE_COLUMNS_NODE_TYPE as MERGE_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    NUMERIC_COLUMN_OPERATION_NODE_TYPE as NUMERIC_COLUMN_OPERATION_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    PARSE_DATETIME_NODE_TYPE as PARSE_DATETIME_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    PLUGIN_NODE_TYPE as PLUGIN_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    RENAME_COLUMNS_NODE_TYPE as RENAME_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    REORDER_COLUMNS_NODE_TYPE as REORDER_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    REPLACE_TEXT_NODE_TYPE as REPLACE_TEXT_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    SAVE_MEMORY_TABLE_NODE_TYPE as SAVE_MEMORY_TABLE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    SAVE_RUN_TABLE_NODE_TYPE as SAVE_RUN_TABLE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    SUB_WORKFLOW_NODE_TYPE as SUB_WORKFLOW_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    UNCONDITIONAL_JUMP_NODE_TYPE as UNCONDITIONAL_JUMP_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    UNPIVOT_ROWS_NODE_TYPE as UNPIVOT_ROWS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    WRITE_BACK_TABLE_NODE_TYPE as WRITE_BACK_TABLE_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_node_types import (
    WRITE_SELECTED_COLUMNS_NODE_TYPE as WRITE_SELECTED_COLUMNS_NODE_TYPE,
)
from flowweaver.nodes.builtin_table_runner import (
    BuiltinTableNodeRunner as BuiltinTableNodeRunner,
)
from flowweaver.nodes.file_table_nodes import (
    BatchRenameFilesNodeHandler as BatchRenameFilesNodeHandler,
)
from flowweaver.nodes.file_table_nodes import (
    ListFilesNodeHandler as ListFilesNodeHandler,
)
from flowweaver.nodes.plugin_table_node import (
    PluginNodeHandler as PluginNodeHandler,
)
from flowweaver.nodes.sql_mapping_table_node import (
    SqlMappingNodeHandler as SqlMappingNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    ConditionalJumpNodeHandler as ConditionalJumpNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    ConditionFlagNodeHandler as ConditionFlagNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    JumpAnchorNodeHandler as JumpAnchorNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    LoopJudgeNodeHandler as LoopJudgeNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    LoopStartNodeHandler as LoopStartNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    SubWorkflowNodeHandler as SubWorkflowNodeHandler,
)
from flowweaver.nodes.table_control_nodes import (
    UnconditionalJumpNodeHandler as UnconditionalJumpNodeHandler,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeHandlerRegistry,
)
from flowweaver.nodes.table_node_handlers import (
    BuiltinTableNodeValidationError as BuiltinTableNodeValidationError,
)
from flowweaver.nodes.table_transform_nodes import (
    AddColumnsNodeHandler as AddColumnsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    AddCurrentDateTimeColumnNodeHandler as AddCurrentDateTimeColumnNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    AdvancedFilterRowsNodeHandler as AdvancedFilterRowsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    CopyColumnNodeHandler as CopyColumnNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    CopyRowsNodeHandler as CopyRowsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    DeduplicateRowsNodeHandler as DeduplicateRowsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    DeleteColumnsNodeHandler as DeleteColumnsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    DeleteRowsNodeHandler as DeleteRowsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    ExtractTextNodeHandler as ExtractTextNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    FillCellsNodeHandler as FillCellsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    FillRangeNodeHandler as FillRangeNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    FillSequenceNodeHandler as FillSequenceNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    FilterRowsNodeHandler as FilterRowsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    GenerateTestTableNodeHandler as GenerateTestTableNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    LookupMatchedFieldNameNodeHandler as LookupMatchedFieldNameNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    MergeColumnsNodeHandler as MergeColumnsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    NumericColumnOperationNodeHandler as NumericColumnOperationNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    ParseDateTimeNodeHandler as ParseDateTimeNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    RenameColumnsNodeHandler as RenameColumnsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    ReorderColumnsNodeHandler as ReorderColumnsNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    ReplaceTextNodeHandler as ReplaceTextNodeHandler,
)
from flowweaver.nodes.table_transform_nodes import (
    UnpivotRowsNodeHandler as UnpivotRowsNodeHandler,
)
from flowweaver.nodes.table_write_nodes import (
    SaveMemoryTableNodeHandler as SaveMemoryTableNodeHandler,
)
from flowweaver.nodes.table_write_nodes import (
    SaveRunTableNodeHandler as SaveRunTableNodeHandler,
)
from flowweaver.nodes.table_write_nodes import (
    WriteBackTableNodeHandler as WriteBackTableNodeHandler,
)
from flowweaver.nodes.table_write_nodes import (
    WriteSelectedColumnsNodeHandler as WriteSelectedColumnsNodeHandler,
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

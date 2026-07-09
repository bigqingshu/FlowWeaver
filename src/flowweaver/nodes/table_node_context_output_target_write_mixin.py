from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from flowweaver.nodes.table_node_output_target_models import (
    TableNodeOutputContext,
)
from flowweaver.nodes.table_node_output_targets import (
    TableOutputWriteResult,
)
from flowweaver.nodes.table_node_output_targets import (
    find_latest_output_target_ref as _find_latest_output_target_ref,
)
from flowweaver.nodes.table_node_output_targets import (
    publish_output_target_batches as _publish_output_target_batches,
)
from flowweaver.nodes.table_node_output_targets import (
    replace_output_target_batches as _replace_output_target_batches,
)
from flowweaver.nodes.table_node_output_targets import (
    require_existing_output_target_ref as _require_existing_output_target_ref,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTarget,
)


class TableNodeContextOutputTargetWriteMixin:
    def find_latest_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel | None:
        return _find_latest_output_target_ref(
            cast(TableNodeOutputContext, self),
            workflow_run_id=workflow_run_id,
            target=target,
        )

    def require_existing_output_target_ref(
        self,
        *,
        workflow_run_id: str,
        target: TableOutputTarget,
    ) -> TableRefModel:
        return _require_existing_output_target_ref(
            cast(TableNodeOutputContext, self),
            workflow_run_id=workflow_run_id,
            target=target,
        )

    def publish_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.publish_output_target_batches(
            task,
            target=target,
            output_name=output_name,
            schema=schema,
            row_batches=(rows,),
        )

    def publish_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        output_name: str,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        return _publish_output_target_batches(
            cast(TableNodeOutputContext, self),
            task,
            target=target,
            output_name=output_name,
            schema=schema,
            row_batches=row_batches,
        )

    def replace_output_target_rows(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        rows: Sequence[dict[str, Any]],
    ) -> TableOutputWriteResult:
        return self.replace_output_target_batches(
            task,
            target=target,
            schema=schema,
            row_batches=(rows,),
        )

    def replace_output_target_batches(
        self,
        task: NodeTaskModel,
        *,
        target: TableOutputTarget,
        schema: Sequence[FieldSchemaModel],
        row_batches: Iterable[Sequence[dict[str, Any]]],
    ) -> TableOutputWriteResult:
        return _replace_output_target_batches(
            cast(TableNodeOutputContext, self),
            task,
            target=target,
            schema=schema,
            row_batches=row_batches,
        )

from __future__ import annotations

from flowweaver.workflow.definition import (
    ControlProtocolMode,
    WorkflowDefinitionModel,
)
from flowweaver.workflow_process.dag_models import (
    DagLoopRegion,
    LoopExitDependency,
    WorkflowDag,
)


def build_loop_regions(
    definition: WorkflowDefinitionModel,
    node_id_set: set[str],
) -> tuple[DagLoopRegion, ...]:
    protocol = definition.control_protocol
    if protocol is None or protocol.mode != ControlProtocolMode.ENABLED:
        return ()
    regions: list[DagLoopRegion] = []
    for region in protocol.loop_regions:
        if not region.enabled:
            continue
        member_node_ids = tuple(
            node_id
            for node_id in (
                region.start_node_id,
                *region.body_node_ids,
                region.judge_node_id,
            )
            if node_id in node_id_set
        )
        regions.append(
            DagLoopRegion(
                loop_id=region.loop_id,
                start_node_instance_id=region.start_node_id,
                judge_node_instance_id=region.judge_node_id,
                body_node_instance_ids=tuple(region.body_node_ids),
                end_node_instance_id=(
                    region.end_node_id if region.end_node_id in node_id_set else None
                ),
                member_node_instance_ids=member_node_ids,
            )
        )
    return tuple(regions)


def build_loop_exit_dependencies(
    regions: tuple[DagLoopRegion, ...],
) -> tuple[LoopExitDependency, ...]:
    dependencies: list[LoopExitDependency] = []
    for region in regions:
        if region.end_node_instance_id is not None:
            dependencies.append(
                LoopExitDependency(
                    node_instance_id=region.end_node_instance_id,
                    loop_id=region.loop_id,
                )
            )
    return tuple(dependencies)


def loop_exit_dependencies_for_node(
    dag: WorkflowDag,
    node_instance_id: str,
) -> tuple[LoopExitDependency, ...]:
    return tuple(
        dependency
        for dependency in dag.loop_exit_dependencies
        if dependency.node_instance_id == node_instance_id
    )


def loop_region_for_loop_id(
    dag: WorkflowDag,
    loop_id: str,
) -> DagLoopRegion | None:
    for region in dag.loop_regions:
        if region.loop_id == loop_id:
            return region
    return None


def node_has_loop_exit_dependency(
    dependencies: tuple[LoopExitDependency, ...],
    node_instance_id: str,
) -> bool:
    return any(
        dependency.node_instance_id == node_instance_id for dependency in dependencies
    )

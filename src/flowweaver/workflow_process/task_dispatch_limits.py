from __future__ import annotations

from flowweaver.engine.runtime_store import RuntimeStore
from flowweaver.workflow_process.ready_queue import count_in_flight_node_runs


def available_ready_dispatch_slots(
    *,
    store: RuntimeStore,
    workflow_run_id: str,
    max_ready_dispatch_per_cycle: int | None,
    max_concurrent_node_tasks: int | None,
) -> int | None:
    limits: list[int] = []
    if max_ready_dispatch_per_cycle is not None:
        limits.append(max(0, max_ready_dispatch_per_cycle))
    if max_concurrent_node_tasks is not None:
        in_flight_count = count_in_flight_node_runs(
            store=store,
            workflow_run_id=workflow_run_id,
        )
        limits.append(max(0, max_concurrent_node_tasks - in_flight_count))
    if not limits:
        return None
    return min(limits)

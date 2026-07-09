from __future__ import annotations

from collections import defaultdict, deque


def topological_sort(
    node_ids: list[str],
    downstream: dict[str, set[str]],
    upstream: dict[str, set[str]],
) -> list[str]:
    indegree = {node_id: len(upstream[node_id]) for node_id in node_ids}
    queue = deque([node_id for node_id in node_ids if indegree[node_id] == 0])
    order: list[str] = []
    reverse_index = defaultdict(list)
    for node_id, children in downstream.items():
        for child in children:
            reverse_index[node_id].append(child)

    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for child in sorted(reverse_index[node_id]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(node_ids):
        raise ValueError("Workflow DAG contains a cycle")
    return order

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import NodeRun
from flowweaver.protocols.enums import (
    LifecycleStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel
from flowweaver.workflow_process.table_input_resolver import (
    TableInputResolutionStatus,
    resolve_configured_input_refs,
)


@dataclass(frozen=True)
class _FakeResult:
    output_refs: list[str]


class _FakeStore:
    def __init__(
        self,
        *,
        results_by_node_run: dict[str, _FakeResult],
        table_refs: dict[str, TableRefModel],
    ) -> None:
        self._results_by_node_run = results_by_node_run
        self._table_refs = table_refs

    def get_latest_succeeded_node_task_result_for_node_run(
        self,
        node_run_id: str,
    ) -> _FakeResult | None:
        return self._results_by_node_run.get(node_run_id)

    def get_table_ref(self, table_ref_id: str) -> TableRefModel | None:
        return self._table_refs.get(table_ref_id)


def test_resolves_named_input_slots_from_list_config() -> None:
    source = _node_run("source-run", "source")
    rules_ref = _table_ref(
        "rules-ref",
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
        logical_table_id="rules_table",
        opaque_handle={"output_slot": "rules_table"},
    )
    store = _FakeStore(
        results_by_node_run={source.node_run_id: _FakeResult(["rules-ref"])},
        table_refs={"rules-ref": rules_ref},
    )

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_sources": [
                {
                    "slot": "rules",
                    "type": "upstream_table",
                    "source_node_instance_id": "source",
                    "output_role": "AUXILIARY",
                    "storage_kind": "MEMORY",
                    "output_slot": "rules_table",
                }
            ]
        },
        upstream_node_runs={"source": source},
    )

    assert result.status == TableInputResolutionStatus.RESOLVED
    assert result.input_refs == ("rules-ref",)
    assert result.input_slot_bindings == {"rules": "rules-ref"}


def test_duplicate_input_slots_are_rejected() -> None:
    source = _node_run("source-run", "source")
    store = _FakeStore(results_by_node_run={}, table_refs={})

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
            },
            "input_sources": {
                "in": {
                    "type": "upstream_table",
                    "source_node_instance_id": "source",
                }
            },
        },
        upstream_node_runs={"source": source},
    )

    assert result.status == TableInputResolutionStatus.ERROR
    assert result.issue is not None
    assert result.issue.slot == "in"
    assert result.issue.message == "duplicate input slot: in"


def test_selector_reports_multiple_matching_upstream_tables() -> None:
    source = _node_run("source-run", "source")
    first_ref = _table_ref(
        "first-ref",
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
    )
    second_ref = _table_ref(
        "second-ref",
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
    )
    store = _FakeStore(
        results_by_node_run={
            source.node_run_id: _FakeResult(["first-ref", "second-ref"])
        },
        table_refs={
            "first-ref": first_ref,
            "second-ref": second_ref,
        },
    )

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
                "output_role": "AUXILIARY",
                "storage_kind": "MEMORY",
            }
        },
        upstream_node_runs={"source": source},
    )

    assert result.status == TableInputResolutionStatus.ERROR
    assert result.issue is not None
    assert result.issue.message == (
        "Input table selector matched multiple upstream tables"
    )
    assert result.issue.details["matched_table_ref_ids"] == [
        "first-ref",
        "second-ref",
    ]


def test_selector_ignores_unreadable_table_refs() -> None:
    source = _node_run("source-run", "source")
    unreadable_ref = _table_ref(
        "unreadable-ref",
        node_run_id=source.node_run_id,
        role=TableRole.AUXILIARY,
        storage_kind=TableStorageKind.MEMORY,
        capabilities=set(),
    )
    store = _FakeStore(
        results_by_node_run={
            source.node_run_id: _FakeResult(["unreadable-ref"])
        },
        table_refs={"unreadable-ref": unreadable_ref},
    )

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
                "output_role": "AUXILIARY",
                "storage_kind": "MEMORY",
            }
        },
        upstream_node_runs={"source": source},
    )

    assert result.status == TableInputResolutionStatus.ERROR
    assert result.issue is not None
    assert result.issue.message == (
        "Input table selector did not match any upstream table"
    )


def test_selector_waits_when_upstream_result_is_not_available() -> None:
    source = _node_run("source-run", "source")
    store = _FakeStore(results_by_node_run={}, table_refs={})

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "source",
            }
        },
        upstream_node_runs={"source": source},
    )

    assert result.status == TableInputResolutionStatus.WAITING
    assert result.issue is None


def test_selector_rejects_non_upstream_source_node() -> None:
    store = _FakeStore(results_by_node_run={}, table_refs={})

    result = resolve_configured_input_refs(
        store=store,
        config={
            "input_source": {
                "type": "upstream_table",
                "source_node_instance_id": "missing-source",
            }
        },
        upstream_node_runs={},
    )

    assert result.status == TableInputResolutionStatus.ERROR
    assert result.issue is not None
    assert result.issue.message == (
        "Input table source node is not a ready upstream dependency"
    )


def _node_run(node_run_id: str, node_instance_id: str) -> NodeRun:
    return NodeRun(
        node_run_id=node_run_id,
        workflow_run_id="run-1",
        node_instance_id=node_instance_id,
        node_type="test.node",
        status="SUCCEEDED",
        state_version=1,
        executor_id=None,
        progress=None,
        current_stage=None,
        attempt=1,
        started_at=None,
        finished_at=None,
        last_heartbeat=None,
        error=None,
    )


def _table_ref(
    table_ref_id: str,
    *,
    node_run_id: str,
    role: TableRole,
    storage_kind: TableStorageKind,
    logical_table_id: str | None = None,
    opaque_handle: dict[str, Any] | None = None,
    capabilities: set[str] | None = None,
    created_at: datetime | None = None,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=role,
        storage_kind=storage_kind,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=(
            TableMutability.WORKING_MUTABLE
            if storage_kind == TableStorageKind.MEMORY
            else TableMutability.PUBLISHED_IMMUTABLE
        ),
        provider_id=(
            "memory"
            if storage_kind == TableStorageKind.MEMORY
            else "sqlite_runtime"
        ),
        logical_table_id=logical_table_id or table_ref_id,
        opaque_handle=opaque_handle or {},
        schema=[
            FieldSchemaModel(
                field_id="amount",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{table_ref_id}-fingerprint",
        version=1,
        capabilities={"READ"} if capabilities is None else capabilities,
        lifecycle_status=(
            LifecycleStatus.ACTIVE
            if storage_kind == TableStorageKind.MEMORY
            else LifecycleStatus.PUBLISHED
        ),
        created_by_workflow_run_id="run-1",
        created_by_node_run_id=node_run_id,
        created_at=created_at or utc_now(),
    )

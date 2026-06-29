from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.node_executor import BuiltinSharedTableNodeExecutor
from flowweaver.nodes.builtin_shared_table import (
    PUBLISH_SHARED_TABLES_NODE_TYPE,
    READ_SHARED_TABLES_NODE_TYPE,
)
from flowweaver.nodes.permissions import resolve_builtin_node_permissions
from flowweaver.protocols.enums import (
    LifecycleStatus,
    NodeResultStatus,
    TableMutability,
    TableRole,
    TableScope,
    TableStorageKind,
)
from flowweaver.protocols.node_task import NodeTaskModel
from flowweaver.protocols.permissions import PermissionGrantModel
from flowweaver.protocols.table_ref import FieldSchemaModel, TableRefModel


def alembic_config(database_path: Path) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    return config


def migrate(database_path: Path) -> None:
    command.upgrade(alembic_config(database_path), "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def create_workflow_run(
    store: RuntimeStore,
    *,
    workflow_id: str,
    workflow_run_id: str,
) -> None:
    workflow = store.create_workflow_definition(
        name=f"Workflow {workflow_id}",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id=workflow_id,
    )
    store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id=workflow_run_id,
    )
    store.create_node_run(
        workflow_run_id=workflow_run_id,
        node_instance_id=f"{workflow_id}-node",
        node_type="builtin.test",
        node_run_id=f"{workflow_run_id}-node",
    )


def make_table_ref(
    *,
    table_ref_id: str,
    workflow_run_id: str,
    node_run_id: str,
    logical_table_id: str,
    version: int,
) -> TableRefModel:
    return TableRefModel(
        table_ref_id=table_ref_id,
        role=TableRole.CURRENT,
        storage_kind=TableStorageKind.RUNTIME_SQL,
        scope=TableScope.WORKFLOW_SCOPE,
        mutability=TableMutability.PUBLISHED_IMMUTABLE,
        provider_id="sqlite_runtime",
        resource_profile_id=None,
        mount_id=None,
        logical_table_id=logical_table_id,
        opaque_handle={
            "database_path": "runtime/run.db",
            "table_name": f"{logical_table_id}_v{version}",
        },
        schema=[
            FieldSchemaModel(
                field_id=f"{logical_table_id}-field-1",
                name="amount",
                data_type="FLOAT",
                nullable=False,
                ordinal=0,
            )
        ],
        schema_fingerprint=f"{logical_table_id}-fingerprint-{version}",
        version=version,
        capabilities={"READ"},
        lifecycle_status=LifecycleStatus.PUBLISHED,
        created_by_workflow_run_id=workflow_run_id,
        created_by_node_run_id=node_run_id,
        created_at=utc_now(),
    )


def make_task(
    *,
    workflow_run_id: str,
    node_type: str,
    node_instance_id: str,
    config: dict,
    input_refs: list[str] | None = None,
) -> NodeTaskModel:
    return NodeTaskModel(
        workflow_run_id=workflow_run_id,
        workflow_process_id=f"{workflow_run_id}-process",
        process_generation=1,
        node_run_id=f"{node_instance_id}-run",
        node_instance_id=node_instance_id,
        node_type=node_type,
        node_version="1.0",
        attempt=1,
        input_refs=input_refs or [],
        config=config,
        timeout_seconds=60,
    )


def grant_task_permissions(store: RuntimeStore, task: NodeTaskModel) -> NodeTaskModel:
    request = resolve_builtin_node_permissions(task)
    grant = store.create_permission_grant(
        PermissionGrantModel(
            request_id=request.request_id,
            workflow_run_id=request.workflow_run_id,
            node_run_id=request.node_run_id,
            scopes=request.scopes,
            granted=True,
            audit_level=request.audit_level,
        )
    )
    return task.model_copy(
        update={"permission_handle_id": grant.permission_handle_id}
    )


def test_publish_shared_tables_node_creates_publication(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    customers = make_table_ref(
        table_ref_id="table-customers-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="customers",
        version=1,
    )
    store.register_table_ref(orders)
    store.register_table_ref(customers)
    executor = BuiltinSharedTableNodeExecutor(
        executor_id="shared-executor-1",
        store=store,
    )

    result = executor.execute(
        grant_task_permissions(
            store,
            make_task(
                workflow_run_id="run-producer",
                node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
                node_instance_id="publish",
                input_refs=[orders.table_ref_id, customers.table_ref_id],
                config={
                    "share_name": "daily_report",
                    "export_names": ["orders", "customers"],
                    "retention_seconds": 3600,
                },
            ),
        )
    )

    publication = store.get_latest_shared_publication("daily_report")
    assert publication is not None
    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.output_refs == [
        (
            "shared-publication:"
            f"daily_report:1:{publication.publication_id}"
        )
    ]
    assert publication.retention_policy == {"retention_seconds": 3600}
    assert [
        (member.export_name, member.table_ref_id)
        for member in publication.members
    ] == [
        ("customers", customers.table_ref_id),
        ("orders", orders.table_ref_id),
    ]


def test_publish_shared_tables_node_rejects_missing_publish_permission(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    executor = BuiltinSharedTableNodeExecutor(
        executor_id="shared-executor-1",
        store=store,
    )

    result = executor.execute(
        make_task(
            workflow_run_id="run-producer",
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_instance_id="publish",
            input_refs=[orders.table_ref_id],
            config={
                "share_name": "daily_report",
                "export_names": ["orders"],
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert result.error["error_code"] == "VALIDATION_ERROR"
    assert result.error["message"] == "Node task is missing permission_handle_id"
    assert store.get_latest_shared_publication("daily_report") is None


def test_read_shared_tables_node_returns_fixed_table_refs(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    create_workflow_run(
        store,
        workflow_id="workflow-consumer",
        workflow_run_id="run-consumer",
    )
    orders_v1 = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    customers_v1 = make_table_ref(
        table_ref_id="table-customers-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="customers",
        version=1,
    )
    orders_v2 = make_table_ref(
        table_ref_id="table-orders-v2",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=2,
    )
    for table_ref in (orders_v1, customers_v1, orders_v2):
        store.register_table_ref(table_ref)
    store.create_shared_publication(
        publication_id="publication-v1",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={
            "orders": orders_v1.table_ref_id,
            "customers": customers_v1.table_ref_id,
        },
    )
    store.create_shared_publication(
        publication_id="publication-v2",
        share_name="daily_report",
        producer_workflow_id="workflow-producer",
        producer_run_id="run-producer",
        members={"orders": orders_v2.table_ref_id},
    )
    executor = BuiltinSharedTableNodeExecutor(store=store)

    result = executor.execute(
        make_task(
            workflow_run_id="run-consumer",
            node_type=READ_SHARED_TABLES_NODE_TYPE,
            node_instance_id="read",
            config={
                "share_name": "daily_report",
                "version_policy": "EXACT_VERSION",
                "exact_version": 1,
                "selected_members": ["customers", "orders"],
            },
        )
    )

    assert result.status == NodeResultStatus.SUCCEEDED
    assert result.output_refs == ["table-customers-v1", "table-orders-v1"]
    loaded_run = store.get_workflow_run("run-consumer")
    assert loaded_run is not None
    assert loaded_run.input_snapshot_id is not None
    snapshot = store.get_input_snapshot(loaded_run.input_snapshot_id)
    assert snapshot is not None
    assert snapshot.inputs[0].publication_id == "publication-v1"
    assert snapshot.inputs[0].selected_members == ("customers", "orders")
    leases = store.list_read_leases_by_workflow_run("run-consumer")
    assert len(leases) == 1
    assert leases[0].publication_id == "publication-v1"
    assert leases[0].selected_members == ("customers", "orders")


def test_publish_shared_tables_node_rejects_mismatched_export_names(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    executor = BuiltinSharedTableNodeExecutor(store=store)

    result = executor.execute(
        make_task(
            workflow_run_id="run-producer",
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_instance_id="publish",
            input_refs=[orders.table_ref_id],
            config={
                "share_name": "daily_report",
                "export_names": ["orders", "customers"],
            },
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.output_refs == []
    assert result.error is not None
    assert "config.export_names must match input_refs" in result.error["message"]
    assert store.get_latest_shared_publication("daily_report") is None


def test_publish_shared_tables_node_requires_export_names(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    create_workflow_run(
        store,
        workflow_id="workflow-producer",
        workflow_run_id="run-producer",
    )
    orders = make_table_ref(
        table_ref_id="table-orders-v1",
        workflow_run_id="run-producer",
        node_run_id="run-producer-node",
        logical_table_id="orders",
        version=1,
    )
    store.register_table_ref(orders)
    executor = BuiltinSharedTableNodeExecutor(store=store)

    result = executor.execute(
        make_task(
            workflow_run_id="run-producer",
            node_type=PUBLISH_SHARED_TABLES_NODE_TYPE,
            node_instance_id="publish",
            input_refs=[orders.table_ref_id],
            config={"share_name": "daily_report"},
        )
    )

    assert result.status == NodeResultStatus.FAILED
    assert result.error is not None
    assert "config.export_names must be a list" in result.error["message"]
    assert store.get_latest_shared_publication("daily_report") is None

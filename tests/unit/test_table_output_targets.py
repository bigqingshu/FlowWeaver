from flowweaver.protocols.enums import TableRole, TableStorageKind
from flowweaver.workflow_process.table_output_targets import (
    TableOutputTargetKind,
    TableOutputTargetResolutionStatus,
    default_current_output_target,
    resolve_configured_output_targets,
)


def test_default_current_output_target_is_unnamed_current_table() -> None:
    target = default_current_output_target("result_table")

    assert target.slot == "result_table"
    assert target.target_kind == TableOutputTargetKind.CURRENT
    assert target.role == TableRole.CURRENT
    assert target.storage_kind is None
    assert target.logical_table_id is None
    assert target.is_new_target is False
    assert target.is_existing_target is False


def test_resolves_new_memory_and_existing_runtime_sql_targets() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_targets": {
                "memory_copy": {
                    "target_kind": "new_memory",
                    "table_name": "orders_memory",
                },
                "stage_orders": {
                    "target_kind": "existing_runtime_sql",
                    "logical_table_id": "stage_orders",
                },
            }
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.RESOLVED
    assert resolution.issue is None
    assert [
        (
            target.slot,
            target.target_kind,
            target.role,
            target.storage_kind,
            target.logical_table_id,
            target.is_new_target,
            target.is_existing_target,
        )
        for target in resolution.targets
    ] == [
        (
            "memory_copy",
            TableOutputTargetKind.NEW_MEMORY,
            TableRole.AUXILIARY,
            TableStorageKind.MEMORY,
            "orders_memory",
            True,
            False,
        ),
        (
            "stage_orders",
            TableOutputTargetKind.EXISTING_RUNTIME_SQL,
            TableRole.AUXILIARY,
            TableStorageKind.RUNTIME_SQL,
            "stage_orders",
            False,
            True,
        ),
    ]


def test_resolves_output_save_as_auxiliary_target() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_save": {
                "enabled": True,
                "target_type": "run_table",
                "table_name": "debug_stage",
            }
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.RESOLVED
    assert resolution.targets[0].slot == "saved_table"
    assert resolution.targets[0].target_kind == TableOutputTargetKind.NEW_RUNTIME_SQL
    assert resolution.targets[0].storage_kind == TableStorageKind.RUNTIME_SQL
    assert resolution.targets[0].logical_table_id == "debug_stage"


def test_resolves_output_targets_from_list_config_and_aliases() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_table_targets": [
                {
                    "output_slot": "current_out",
                    "target_type": "current_table",
                },
                {
                    "slot": "memory_out",
                    "target_type": "memory_table",
                    "target_table": "memory_stage",
                },
                {
                    "slot": "runtime_out",
                    "target_type": "run_table",
                    "table_name": "runtime_stage",
                },
            ]
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.RESOLVED
    assert [
        (
            target.slot,
            target.target_kind,
            target.role,
            target.storage_kind,
            target.logical_table_id,
        )
        for target in resolution.targets
    ] == [
        (
            "current_out",
            TableOutputTargetKind.CURRENT,
            TableRole.CURRENT,
            None,
            None,
        ),
        (
            "memory_out",
            TableOutputTargetKind.NEW_MEMORY,
            TableRole.AUXILIARY,
            TableStorageKind.MEMORY,
            "memory_stage",
        ),
        (
            "runtime_out",
            TableOutputTargetKind.NEW_RUNTIME_SQL,
            TableRole.AUXILIARY,
            TableStorageKind.RUNTIME_SQL,
            "runtime_stage",
        ),
    ]


def test_current_output_target_rejects_table_name() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_target": {
                "slot": "out",
                "target_kind": "current",
                "table_name": "should_not_exist",
            }
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.ERROR
    assert resolution.issue is not None
    assert resolution.issue.message == "current output target must not be named"


def test_named_output_target_requires_table_name() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_target": {
                "slot": "memory",
                "target_kind": "new_memory",
            }
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.ERROR
    assert resolution.issue is not None
    assert resolution.issue.message == "new_memory requires table_name"


def test_duplicate_output_target_slots_are_rejected() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_target": {
                "slot": "memory",
                "target_kind": "new_memory",
                "table_name": "a",
            },
            "output_targets": {
                "memory": {
                    "target_kind": "new_runtime_sql",
                    "table_name": "b",
                }
            },
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.ERROR
    assert resolution.issue is not None
    assert resolution.issue.message == "duplicate output target slot: memory"


def test_output_target_list_requires_slot() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_targets": [
                {
                    "target_kind": "new_memory",
                    "table_name": "scratch",
                }
            ]
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.ERROR
    assert resolution.issue is not None
    assert resolution.issue.message == "output_targets[0] must include slot"


def test_unsupported_output_target_kind_is_rejected() -> None:
    resolution = resolve_configured_output_targets(
        {
            "output_target": {
                "slot": "out",
                "target_kind": "external_sql",
                "table_name": "orders",
            }
        }
    )

    assert resolution.status == TableOutputTargetResolutionStatus.ERROR
    assert resolution.issue is not None
    assert resolution.issue.message == "unsupported output target kind: external_sql"


def test_missing_config_returns_no_config() -> None:
    resolution = resolve_configured_output_targets({})

    assert resolution.status == TableOutputTargetResolutionStatus.NO_CONFIG
    assert resolution.targets == ()

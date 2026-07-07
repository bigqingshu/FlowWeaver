from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from flowweaver.engine.runtime_store import RuntimeStore, sqlite_url
from flowweaver.protocols.enums import (
    LoopIterationRunStatus,
    LoopRunStatus,
)
from flowweaver.workflow_process.loop_control import (
    ControlSignal,
    SerialLoopAdvanceStatus,
    SerialLoopInspectionStatus,
    SerialLoopStartStatus,
    advance_serial_loop_from_decision,
    inspect_serial_loop_state,
    start_serial_loop,
    workflow_loop_runs_are_terminal,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    command.upgrade(config, "head")


def make_store(tmp_path: Path) -> RuntimeStore:
    database_path = tmp_path / "metadata.db"
    migrate(database_path)
    return RuntimeStore.from_sqlite_path(database_path)


def create_loop(
    store: RuntimeStore,
    *,
    max_iterations: int = 3,
) -> str:
    workflow = store.create_workflow_definition(
        name="Loop control workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-loop-control",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-loop-control",
    )
    loop = store.create_loop_run(
        loop_run_id="loop-run-1",
        workflow_run_id=run.workflow_run_id,
        loop_id="orders_loop",
        start_node_instance_id="loop-start",
        judge_node_instance_id="loop-judge",
        max_iterations=max_iterations,
    )
    assert loop is not None
    return loop.loop_run_id


def real_continue_signal() -> ControlSignal:
    return ControlSignal.from_row(
        {
            "signal_type": "loop_decision",
            "selected_branch": "continue_loop",
            "actual_control": "true",
            "source_node_id": "loop-judge",
            "target_anchor": "orders_loop",
            "details": '{"loop_id":"orders_loop"}',
        }
    )


def real_end_signal() -> ControlSignal:
    return ControlSignal.from_row(
        {
            "signal_type": "loop_decision",
            "selected_branch": "end_loop",
            "actual_control": "true",
        }
    )


def test_start_serial_loop_creates_first_running_iteration(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)

    started = start_serial_loop(
        store,
        loop_run_id=loop_run_id,
        first_input_selector={"row_index": 0},
    )
    duplicate = start_serial_loop(store, loop_run_id=loop_run_id)

    assert started.status == SerialLoopStartStatus.STARTED
    assert started.loop_run is not None
    assert started.loop_run.status == LoopRunStatus.RUNNING.value
    assert started.loop_run.current_iteration == 0
    assert started.iteration is not None
    assert started.iteration.status == LoopIterationRunStatus.RUNNING.value
    assert started.iteration.iteration_index == 0
    assert started.iteration.input_selector == {"row_index": 0}
    assert duplicate.status == SerialLoopStartStatus.ALREADY_STARTED
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1


def test_inspect_serial_loop_state_tracks_recovery_boundaries(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)

    before_start = inspect_serial_loop_state(store, loop_run_id=loop_run_id)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    active = inspect_serial_loop_state(store, loop_run_id=loop_run_id)
    assert started.iteration is not None
    succeeded = store.update_loop_iteration_run_status(
        started.iteration.loop_iteration_id,
        LoopIterationRunStatus.SUCCEEDED,
        expected_state_version=started.iteration.state_version,
        allowed_source_statuses=[LoopIterationRunStatus.RUNNING],
    )
    waiting = inspect_serial_loop_state(store, loop_run_id=loop_run_id)

    assert before_start.status == SerialLoopInspectionStatus.NOT_STARTED
    assert before_start.next_iteration_index == 0
    assert active.status == SerialLoopInspectionStatus.ACTIVE_ITERATION_RUNNING
    assert active.active_iteration == started.iteration
    assert active.next_iteration_index == 1
    assert succeeded is not None
    assert waiting.status == SerialLoopInspectionStatus.WAITING_FOR_DECISION
    assert waiting.latest_iteration == succeeded
    assert waiting.next_iteration_index == 1


def test_inspect_serial_loop_state_reports_failed_iteration_blocker(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None
    failed = store.update_loop_iteration_run_status(
        started.iteration.loop_iteration_id,
        LoopIterationRunStatus.FAILED,
        expected_state_version=started.iteration.state_version,
        allowed_source_statuses=[LoopIterationRunStatus.RUNNING],
        error={"message": "iteration failed"},
    )

    inspected = inspect_serial_loop_state(store, loop_run_id=loop_run_id)

    assert failed is not None
    assert inspected.status == SerialLoopInspectionStatus.BLOCKED_BY_FAILED_ITERATION
    assert inspected.latest_iteration == failed
    assert inspected.next_iteration_index is None


def test_workflow_loop_terminal_helper_is_ready_for_completion_checks(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    workflow = store.create_workflow_definition(
        name="No loop workflow",
        definition={"schema_version": "1.0", "nodes": [], "connections": []},
        workflow_id="workflow-no-loop",
    )
    run = store.create_workflow_run(
        workflow_id=workflow.workflow_id,
        workflow_run_id="run-no-loop",
    )

    assert workflow_loop_runs_are_terminal(
        store,
        workflow_run_id=run.workflow_run_id,
    )

    loop_run_id = create_loop(store)
    pending_loop = store.get_loop_run(loop_run_id)
    assert pending_loop is not None
    assert not workflow_loop_runs_are_terminal(
        store,
        workflow_run_id=pending_loop.workflow_run_id,
    )
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None
    ended = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_end_signal(),
    )

    assert ended.status == SerialLoopAdvanceStatus.LOOP_ENDED
    assert workflow_loop_runs_are_terminal(
        store,
        workflow_run_id=pending_loop.workflow_run_id,
    )


def test_serial_loop_continue_creates_next_iteration_once(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None

    advanced = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_continue_signal(),
        next_input_selector={"row_index": 1},
    )
    duplicate = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_continue_signal(),
        next_input_selector={"row_index": 1},
    )

    assert advanced.status == SerialLoopAdvanceStatus.CREATED_NEXT_ITERATION
    assert advanced.loop_run is not None
    assert advanced.loop_run.status == LoopRunStatus.RUNNING.value
    assert advanced.loop_run.current_iteration == 1
    assert advanced.completed_iteration is not None
    assert advanced.completed_iteration.status == LoopIterationRunStatus.SUCCEEDED.value
    assert advanced.next_iteration is not None
    assert advanced.next_iteration.iteration_index == 1
    assert advanced.next_iteration.status == LoopIterationRunStatus.RUNNING.value
    assert advanced.next_iteration.input_selector == {"row_index": 1}
    assert duplicate.status == SerialLoopAdvanceStatus.ALREADY_ADVANCED
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 2


def test_serial_loop_end_marks_loop_terminal(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None

    ended = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_end_signal(),
    )
    duplicate = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_end_signal(),
    )

    assert ended.status == SerialLoopAdvanceStatus.LOOP_ENDED
    assert ended.loop_run is not None
    assert ended.loop_run.status == LoopRunStatus.ENDED.value
    assert ended.loop_run.exit_reason == "end_loop"
    assert ended.completed_iteration is not None
    assert ended.completed_iteration.status == LoopIterationRunStatus.SUCCEEDED.value
    assert duplicate.status == SerialLoopAdvanceStatus.ALREADY_ADVANCED
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1


def test_serial_loop_continue_at_max_iterations_stops_without_next_iteration(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store, max_iterations=1)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None

    capped = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_continue_signal(),
    )
    duplicate = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=real_continue_signal(),
    )

    assert capped.status == SerialLoopAdvanceStatus.LOOP_MAX_ITERATIONS_REACHED
    assert capped.loop_run is not None
    assert capped.loop_run.status == LoopRunStatus.MAX_ITERATIONS_REACHED.value
    assert capped.loop_run.current_iteration == 0
    assert capped.loop_run.exit_reason == "max_iterations_reached"
    assert capped.next_iteration is None
    assert duplicate.status == SerialLoopAdvanceStatus.ALREADY_ADVANCED
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1


def test_preview_loop_decision_is_ignored_without_side_effects(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.loop_run is not None
    assert started.iteration is not None

    ignored = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=ControlSignal.from_row(
            {
                "signal_type": "loop_decision",
                "selected_branch": "continue_loop",
                "actual_control": "false",
            }
        ),
    )

    assert ignored.status == SerialLoopAdvanceStatus.IGNORED_PREVIEW_SIGNAL
    assert store.get_loop_run(loop_run_id) == started.loop_run
    assert (
        store.get_loop_iteration_run(started.iteration.loop_iteration_id)
        == started.iteration
    )
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1


def test_invalid_loop_decision_branch_is_rejected(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    loop_run_id = create_loop(store)
    started = start_serial_loop(store, loop_run_id=loop_run_id)
    assert started.iteration is not None

    rejected = advance_serial_loop_from_decision(
        store,
        loop_run_id=loop_run_id,
        loop_iteration_id=started.iteration.loop_iteration_id,
        signal=ControlSignal(
            signal_type="loop_decision",
            selected_branch="unknown_branch",
            actual_control=True,
        ),
    )

    assert rejected.status == SerialLoopAdvanceStatus.REJECTED_BRANCH
    assert len(store.list_loop_iteration_runs(loop_run_id)) == 1

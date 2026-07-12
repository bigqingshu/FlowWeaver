from pathlib import Path

from flowweaver.common.config import EngineConfig
from flowweaver.common.time import utc_now
from flowweaver.engine.runtime_models import WorkflowProcess
from flowweaver.engine.supervisor_commands import workflow_process_command


def test_workflow_process_command_includes_memory_table_soft_row_limit() -> None:
    command = workflow_process_command(
        python_executable="python.exe",
        src_path=Path("src"),
        database_url="sqlite:///runtime.db",
        workflow_run_id="run-1",
        process=WorkflowProcess(
            process_id="process-1",
            workflow_run_id="run-1",
            os_pid=None,
            process_generation=2,
            fencing_token=None,
            status="STARTING",
            started_at=utc_now(),
            last_heartbeat_at=None,
            cancel_requested_at=None,
            exited_at=None,
            exit_code=None,
            error=None,
        ),
        config=EngineConfig(memory_table_soft_row_limit=321),
        runtime_event_path=Path("runtime-events.sock"),
    )

    option_index = command.index("--memory-table-soft-row-limit")
    assert command[option_index + 1] == "321"
    plugin_dir_index = command.index("--plugin-dir")
    assert command[plugin_dir_index + 1] == "plugins"

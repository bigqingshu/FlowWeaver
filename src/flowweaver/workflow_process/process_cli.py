from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Callable

from flowweaver.engine.runtime_event_sink import (
    DatabaseEventSink,
    IPCEventSink,
    RuntimeEventSink,
)
from flowweaver.engine.runtime_store import RuntimeStore


def run_workflow_process_cli(
    argv: list[str] | None,
    *,
    run_workflow_process: Callable[..., int],
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--process-id", required=True)
    parser.add_argument("--process-generation", type=int, required=True)
    parser.add_argument("--heartbeat-interval-seconds", type=float, default=2.0)
    parser.add_argument("--runtime-event-path")
    parser.add_argument("--runtime-dir")
    parser.add_argument("--plugin-dir")
    parser.add_argument("--execution-mode")
    parser.add_argument("--max-concurrent-node-tasks")
    parser.add_argument("--memory-table-soft-row-limit", type=int)
    parser.add_argument("--wait-for-start-signal", action="store_true")
    args = parser.parse_args(argv)
    if args.wait_for_start_signal and sys.stdin.readline().strip() != "START":
        return 1
    store = RuntimeStore(args.database_url)
    try:
        event_sink: RuntimeEventSink = (
            IPCEventSink(args.runtime_event_path)
            if args.runtime_event_path
            else DatabaseEventSink(store)
        )
        return run_workflow_process(
            store=store,
            workflow_run_id=args.workflow_run_id,
            process_id=args.process_id,
            process_generation=args.process_generation,
            heartbeat_interval_seconds=args.heartbeat_interval_seconds,
            event_sink=event_sink,
            runtime_dir=args.runtime_dir,
            plugin_dir=args.plugin_dir,
            execution_mode=args.execution_mode,
            max_concurrent_node_tasks=args.max_concurrent_node_tasks,
            memory_table_soft_row_limit=args.memory_table_soft_row_limit,
        )
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        store.dispose()

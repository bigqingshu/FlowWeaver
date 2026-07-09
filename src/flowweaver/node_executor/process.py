from __future__ import annotations

import argparse
import sys
from typing import TextIO

from flowweaver.node_executor.base import NodeExecutorFactory
from flowweaver.node_executor.process_helpers import (
    write_envelope as _write_envelope,
)
from flowweaver.node_executor.process_loop import (
    EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE as EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE,
)
from flowweaver.node_executor.process_loop import (
    run_node_executor_ipc_loop,
)
from flowweaver.node_executor.process_runtime import (
    NodeExecutorProcess as NodeExecutorProcess,
)


def run_node_executor_process(
    *,
    executor_id: str,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    executor_factory: NodeExecutorFactory | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    process = NodeExecutorProcess(
        executor_id=executor_id,
        executor_factory=executor_factory,
        event_writer=lambda envelope: _write_envelope(stdout, envelope),
    )
    return run_node_executor_ipc_loop(
        process,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executor-id", required=True)
    args = parser.parse_args(argv)
    return run_node_executor_process(executor_id=args.executor_id)


def _exit() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    _exit()

from __future__ import annotations

import os
from threading import Thread
from typing import TYPE_CHECKING, TextIO

from flowweaver.node_executor.process_helpers import write_envelope, write_process_error
from flowweaver.protocols.enums import IPCMessageType
from flowweaver.protocols.ipc_messages import IPCEnvelope

if TYPE_CHECKING:
    from flowweaver.node_executor.process import NodeExecutorProcess

EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE = 2


def run_node_executor_ipc_loop(
    process: NodeExecutorProcess,
    *,
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    write_envelope(stdout, process.ready_envelope())
    task_workers: list[Thread] = []

    def handle_task(envelope: IPCEnvelope) -> None:
        try:
            responses = process.handle_envelope(envelope)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
            os._exit(code)
        for response in responses:
            write_envelope(stdout, response)

    for line in stdin:
        if not line.strip():
            continue
        try:
            envelope = IPCEnvelope.model_validate_json(line)
        except ValueError as exc:
            write_process_error(stderr, "IPC_INPUT_ERROR", exc)
            return EXECUTOR_PROCESS_IPC_ERROR_EXIT_CODE
        if envelope.message_type == IPCMessageType.NODE_TASK_SUBMIT:
            worker = Thread(
                target=handle_task,
                args=(envelope,),
                name=f"flowweaver-executor-task-{envelope.message_id}",
                daemon=True,
            )
            task_workers.append(worker)
            worker.start()
            continue
        responses = process.handle_envelope(envelope)
        for response in responses:
            write_envelope(stdout, response)
    for worker in task_workers:
        worker.join()
    return 0

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import deque
from threading import Event, Lock, Thread
from typing import Any

parser = argparse.ArgumentParser()
parser.add_argument("--executor-id", required=True)
args = parser.parse_args()

output_lock = Lock()
state_lock = Lock()
cancel_event = Event()
event_times: deque[float] = deque()
active_task: dict[str, Any] | None = None
runtime_feedback_policy: dict[str, Any] | None = None
runtime_options_version = 0
last_heartbeat_at = 0.0
last_progress_at = 0.0


def emit(
    message_type: str,
    payload: dict[str, Any],
    *,
    task: dict[str, Any] | None = None,
) -> bool:
    envelope: dict[str, Any] = {
        "message_type": message_type,
        "payload": payload,
    }
    if task is not None:
        envelope["workflow_run_id"] = task["workflow_run_id"]
        envelope["node_run_id"] = task["node_run_id"]
    with output_lock:
        try:
            print(json.dumps(envelope, ensure_ascii=False), flush=True)
        except BrokenPipeError:
            return False
    return True


def policy_snapshot() -> dict[str, Any]:
    with state_lock:
        return dict(runtime_feedback_policy or {})


def event_allowed(policy: dict[str, Any]) -> bool:
    limit = int(policy.get("telemetry", {}).get("event_rate_limit_per_second", 0))
    if limit <= 0:
        return True
    now = time.monotonic()
    with state_lock:
        while event_times and now - event_times[0] >= 1.0:
            event_times.popleft()
        if len(event_times) >= limit:
            return False
        event_times.append(now)
    return True


def level_enabled(configured: str, message_level: str) -> bool:
    levels = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
    return levels.get(message_level, 0) >= levels.get(configured, 100)


def mask_value(value: Any, policy: str) -> Any:
    if policy == "none":
        return value
    if policy == "full":
        return "***"
    text = str(value)
    if len(text) <= 2:
        return "*" * len(text)
    return f"{text[0]}***{text[-1]}"


def sanitize_context(
    context: dict[str, Any],
    policy: dict[str, Any],
    *,
    is_error: bool,
) -> dict[str, Any]:
    diagnostics = policy.get("diagnostics", {})
    forbidden = {"rows", "table_rows", "records", "base64", "bytes", "binary"}
    cleaned = {
        key: value
        for key, value in context.items()
        if key.lower() not in forbidden
    }
    if not diagnostics.get("include_metrics", True):
        cleaned.pop("metrics", None)
    if is_error and not diagnostics.get("capture_error_context", True):
        cleaned = {
            key: value
            for key, value in cleaned.items()
            if key in {"message", "error_code", "reason"}
        }
    mask_policy = diagnostics.get("mask_policy", "partial")
    for column in diagnostics.get("redact_columns", []):
        if column in cleaned:
            cleaned[column] = mask_value(cleaned[column], mask_policy)
    byte_limit = int(diagnostics.get("payload_byte_limit", 65536))
    encoded = json.dumps(cleaned, ensure_ascii=False, default=str).encode("utf-8")
    if byte_limit > 0 and len(encoded) > byte_limit:
        return {
            "_runtime_options_payload_truncated": True,
            "_runtime_options_payload_original_bytes": len(encoded),
        }
    return cleaned


def emit_log(
    task: dict[str, Any],
    level: str,
    message: str,
    context: dict[str, Any] | None = None,
) -> bool:
    policy = policy_snapshot()
    telemetry = policy.get("telemetry", {})
    if not level_enabled(telemetry.get("log_level", "INFO"), level):
        return False
    if not event_allowed(policy):
        return False
    return emit(
        "NODE_TASK_LOG",
        {
            "level": level,
            "message": message[:1024],
            "logger_name": "flowweaver.example.table_projection",
            "node_instance_id": task["node_instance_id"],
            "task_id": task["task_id"],
            "context": sanitize_context(
                context or {},
                policy,
                is_error=level == "ERROR",
            ),
        },
        task=task,
    )


def emit_progress(
    task: dict[str, Any],
    progress: float,
    stage: str,
    copied_rows: int,
    *,
    force: bool = False,
) -> bool:
    global last_progress_at
    policy = policy_snapshot()
    telemetry = policy.get("telemetry", {})
    if not telemetry.get("progress_enabled", True):
        return False
    if telemetry.get("event_level", "verbose") not in {"progress", "verbose"}:
        return False
    now = time.monotonic()
    interval = float(telemetry.get("progress_interval_seconds", 0))
    if not force and now - last_progress_at < interval:
        return False
    if not event_allowed(policy):
        return False
    last_progress_at = now
    metrics = {"copied_rows": copied_rows}
    if not policy.get("diagnostics", {}).get("include_metrics", True):
        metrics = {}
    return emit(
        "NODE_TASK_PROGRESS",
        {
            "progress": max(0.0, min(1.0, progress)),
            "current_stage": stage,
            "metrics": metrics,
        },
        task=task,
    )


def emit_heartbeat(task: dict[str, Any], *, force: bool = False) -> None:
    global last_heartbeat_at
    now = time.monotonic()
    if not force and now - last_heartbeat_at < 1.0:
        return
    last_heartbeat_at = now
    emit(
        "NODE_TASK_HEARTBEAT",
        {
            "executor_id": args.executor_id,
            "task_id": task["task_id"],
            "attempt": task["attempt"],
        },
        task=task,
    )


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def output_schema(
    input_schema: list[dict[str, Any]],
    selected_columns: list[str],
    rename_first_to: str,
) -> list[dict[str, Any]]:
    by_name = {field["name"]: field for field in input_schema}
    missing = [name for name in selected_columns if name not in by_name]
    if missing:
        raise ValueError("unknown selected columns: " + ", ".join(missing))
    if len(selected_columns) != len(set(selected_columns)):
        raise ValueError("selected columns must be unique")
    schema: list[dict[str, Any]] = []
    for ordinal, name in enumerate(selected_columns):
        field = dict(by_name[name])
        field["ordinal"] = ordinal
        if ordinal == 0 and rename_first_to:
            field["name"] = rename_first_to
        schema.append(field)
    output_names = [field["name"] for field in schema]
    if len(output_names) != len(set(output_names)):
        raise ValueError("output column names must be unique")
    return schema


def terminal_result(
    task: dict[str, Any],
    status: str,
    *,
    summary: dict[str, Any],
    outputs: list[dict[str, Any]] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "node_run_id": task["node_run_id"],
        "attempt": task["attempt"],
        "executor_id": args.executor_id,
        "process_generation": task["process_generation"],
        "status": status,
        "summary": summary,
        "error": error,
        "plugin_runtime": {
            "protocol_version": "1",
            "outputs": outputs or [],
        },
    }


def emit_cancelled(task: dict[str, Any], copied_rows: int) -> None:
    result = terminal_result(
        task,
        "CANCELLED",
        summary={"copied_rows": copied_rows},
        error={
            "message": "Node task cancelled cooperatively",
            "reason": "WORKFLOW_CANCEL_REQUESTED",
        },
    )
    emit("NODE_TASK_COMPLETED", {"result": result}, task=task)


def run_projection(task: dict[str, Any]) -> None:
    copied_rows = 0
    input_connection: sqlite3.Connection | None = None
    output_connection: sqlite3.Connection | None = None
    try:
        runtime = task["plugin_runtime"]
        input_ref = runtime["inputs"][0]
        output_target = runtime["output_targets"][0]
        config = task["config"]
        selected_columns = config["selected_columns"]
        if not isinstance(selected_columns, list) or not selected_columns:
            raise ValueError("selected_columns must be a non-empty list")
        if any(not isinstance(name, str) or not name for name in selected_columns):
            raise ValueError("selected_columns must contain non-empty strings")
        rename_first_to = str(config.get("rename_first_to", "")).strip()
        batch_size = max(1, int(config.get("batch_size", 500)))
        schema = output_schema(
            input_ref["schema"],
            selected_columns,
            rename_first_to,
        )
        input_connection = sqlite3.connect(input_ref["database_uri"], uri=True)
        output_connection = sqlite3.connect(output_target["database_path"])
        column_definitions = ", ".join(
            f"{quote_identifier(field['name'])} {field['data_type']}"
            for field in schema
        )
        output_table = quote_identifier(output_target["table_name"])
        output_connection.execute(f"DROP TABLE IF EXISTS {output_table}")
        output_connection.execute(
            f"CREATE TABLE {output_table} ({column_definitions})"
        )
        source_table = quote_identifier(input_ref["table_name"])
        source_columns = ", ".join(
            quote_identifier(name) for name in selected_columns
        )
        total_rows = int(
            input_connection.execute(
                f"SELECT COUNT(*) FROM {source_table}"
            ).fetchone()[0]
        )
        cursor = input_connection.execute(
            f"SELECT {source_columns} FROM {source_table}"
        )
        placeholders = ", ".join("?" for _ in schema)
        insert_sql = f"INSERT INTO {output_table} VALUES ({placeholders})"
        emit_log(task, "INFO", "Projection started", {"total_rows": total_rows})
        emit_heartbeat(task, force=True)
        emit_progress(task, 0.0, "projecting", 0, force=True)
        while True:
            if cancel_event.is_set():
                output_connection.rollback()
                emit_cancelled(task, copied_rows)
                return
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            output_connection.executemany(insert_sql, batch)
            copied_rows += len(batch)
            emit_heartbeat(task)
            emit_progress(
                task,
                copied_rows / total_rows if total_rows else 1.0,
                "projecting",
                copied_rows,
            )
            time.sleep(0)
        output_connection.commit()
        emit_progress(task, 1.0, "completed", copied_rows, force=True)
        emit_log(task, "INFO", "Projection completed", {"copied_rows": copied_rows})
        output = {
            "slot_name": "out",
            "database_path": output_target["database_path"],
            "table_name": output_target["table_name"],
            "schema": schema,
        }
        result = terminal_result(
            task,
            "SUCCEEDED",
            summary={
                "selected_columns": selected_columns,
                "rename_first_to": rename_first_to,
                "copied_rows": copied_rows,
            },
            outputs=[output],
        )
        emit("NODE_TASK_COMPLETED", {"result": result}, task=task)
    except Exception as exc:
        emit_log(
            task,
            "ERROR",
            "Projection failed",
            {"error_code": "REFERENCE_PLUGIN_FAILED", "message": str(exc)},
        )
        result = terminal_result(
            task,
            "FAILED",
            summary={"copied_rows": copied_rows},
            error={
                "error_code": "REFERENCE_PLUGIN_FAILED",
                "message": str(exc),
            },
        )
        emit(
            "NODE_TASK_FAILED",
            {"result": result, "error_type": type(exc).__name__},
            task=task,
        )
    finally:
        if input_connection is not None:
            input_connection.close()
        if output_connection is not None:
            output_connection.close()


emit("EXECUTOR_READY", {"executor_id": args.executor_id})
worker: Thread | None = None
for line in sys.stdin:
    message = json.loads(line)
    message_type = message.get("message_type")
    if message_type == "NODE_TASK_SUBMIT" and active_task is None:
        active_task = message["payload"]
        with state_lock:
            runtime_feedback_policy = active_task.get("runtime_feedback_policy")
            runtime_options_version = active_task.get("runtime_options_version", 0)
        worker = Thread(target=run_projection, args=(active_task,), daemon=False)
        worker.start()
        continue
    if message_type == "NODE_TASK_RUNTIME_OPTIONS_UPDATE" and active_task:
        payload = message["payload"]
        if payload.get("task_id") != active_task["task_id"]:
            continue
        with state_lock:
            if payload["runtime_options_version"] <= runtime_options_version:
                continue
            runtime_feedback_policy = payload["runtime_feedback_policy"]
            runtime_options_version = payload["runtime_options_version"]
            applied_version = runtime_options_version
        emit(
            "NODE_TASK_RUNTIME_OPTIONS_APPLIED",
            {
                "task_id": active_task["task_id"],
                "runtime_options_version": applied_version,
            },
            task=active_task,
        )
        emit_log(
            active_task,
            "WARN",
            "Runtime options applied",
            {"runtime_options_version": applied_version},
        )
        continue
    if message_type == "NODE_TASK_CANCEL_REQUEST" and active_task:
        payload = message["payload"]
        if payload.get("task_id") == active_task["task_id"]:
            cancel_event.set()

if worker is not None:
    worker.join()

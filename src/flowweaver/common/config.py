from __future__ import annotations

from pathlib import Path

from pydantic import Field

from flowweaver.protocols.base import StrictModel


class EngineConfig(StrictModel):
    data_dir: Path = Path("runtime")
    metadata_db_path: Path | None = None
    runtime_dir: Path | None = None
    log_dir: Path | None = None
    temp_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    audit_level: str = "STANDARD"
    local_api_token: str | None = None
    enforce_single_instance: bool = True
    max_concurrent_workflows: int = 4
    max_executors_per_workflow: int = 2
    max_ipc_message_bytes: int = 1024 * 1024
    max_runtime_db_bytes: int = 1024 * 1024 * 1024
    max_log_file_bytes: int = 10 * 1024 * 1024
    staging_ttl_seconds: int = 3600
    orphan_cleanup_interval: int = 300
    workflow_process_heartbeat_interval_seconds: int = 2
    workflow_process_lost_threshold_seconds: int = 10
    workflow_process_start_timeout_seconds: int = 10
    workflow_process_cancel_grace_seconds: int = 5
    supervisor_maintenance_interval_seconds: float = 1.0
    allowed_origins: set[str] = Field(default_factory=lambda: {"http://127.0.0.1"})

    def resolved_metadata_db_path(self) -> Path:
        return self.metadata_db_path or self.data_dir / "metadata" / "flowweaver.db"

    def resolved_runtime_dir(self) -> Path:
        return self.runtime_dir or self.data_dir / "workflow_runs"

    def resolved_log_dir(self) -> Path:
        return self.log_dir or self.data_dir / "logs"

    def resolved_temp_dir(self) -> Path:
        return self.temp_dir or self.data_dir / "temp"

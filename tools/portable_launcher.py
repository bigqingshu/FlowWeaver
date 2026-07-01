from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import urlopen

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_HEALTH_TIMEOUT_SECONDS = 30
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})
APP_IMPORT_TARGET = "flowweaver.api.app:create_default_app"


def configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue


class LauncherConfigurationError(ValueError):
    """Raised when the portable launcher configuration is invalid."""


class LauncherRuntimeError(RuntimeError):
    """Raised when the portable launcher cannot complete a runtime step."""


class PollableProcess(Protocol):
    returncode: int | None

    def poll(self) -> int | None:
        ...

    def terminate(self) -> None:
        ...

    def kill(self) -> None:
        ...

    def wait(self, timeout: float | None = None) -> int:
        ...


@dataclass(frozen=True)
class LauncherSettings:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    no_desktop: bool = False
    health_timeout_seconds: int = DEFAULT_HEALTH_TIMEOUT_SECONDS
    keep_enginehost_on_desktop_exit: bool = False

    def __post_init__(self) -> None:
        if self.host not in ALLOWED_HOSTS:
            raise LauncherConfigurationError(
                "host must be 127.0.0.1 or localhost"
            )
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise LauncherConfigurationError("port must be an integer")
        if self.port < 1 or self.port > 65535:
            raise LauncherConfigurationError("port must be between 1 and 65535")
        if (
            isinstance(self.health_timeout_seconds, bool)
            or not isinstance(self.health_timeout_seconds, int)
        ):
            raise LauncherConfigurationError(
                "health_timeout_seconds must be an integer"
            )
        if self.health_timeout_seconds < 1:
            raise LauncherConfigurationError(
                "health_timeout_seconds must be at least 1"
            )


@dataclass(frozen=True)
class PortableLayout:
    root: Path
    enginehost_dir: Path
    python_exe: Path
    app_module_path: Path
    desktop_dir: Path
    desktop_exe: Path
    runtime_dir: Path
    log_dir: Path
    token_path: Path


@dataclass(frozen=True)
class EngineHostLaunchSpec:
    command: tuple[str, ...]
    cwd: Path
    stdout_path: Path
    stderr_path: Path


@dataclass(frozen=True)
class DesktopLaunchSpec:
    command: tuple[str, ...]
    cwd: Path
    stdout_path: Path
    stderr_path: Path


@dataclass(frozen=True)
class PortableLaunchPlan:
    settings: LauncherSettings
    layout: PortableLayout
    base_url: str
    enginehost: EngineHostLaunchSpec
    desktop: DesktopLaunchSpec | None


def parse_launcher_args(argv: Sequence[str] | None = None) -> LauncherSettings:
    parser = argparse.ArgumentParser(
        description="Launch a FlowWeaver portable EngineHost and Desktop pair."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-desktop", action="store_true")
    parser.add_argument(
        "--health-timeout-seconds",
        type=int,
        default=DEFAULT_HEALTH_TIMEOUT_SECONDS,
    )
    parser.add_argument("--keep-enginehost-on-desktop-exit", action="store_true")
    args = parser.parse_args(argv)
    return LauncherSettings(
        host=args.host,
        port=args.port,
        no_desktop=args.no_desktop,
        health_timeout_seconds=args.health_timeout_seconds,
        keep_enginehost_on_desktop_exit=args.keep_enginehost_on_desktop_exit,
    )


def resolve_portable_layout(portable_root: Path) -> PortableLayout:
    root = portable_root.resolve()
    enginehost_dir = root / "EngineHost"
    desktop_dir = root / "Desktop"
    runtime_dir = enginehost_dir / "runtime"
    log_dir = runtime_dir / "logs"
    return PortableLayout(
        root=root,
        enginehost_dir=enginehost_dir,
        python_exe=enginehost_dir / "python312" / "python.exe",
        app_module_path=enginehost_dir / "src" / "flowweaver" / "api" / "app.py",
        desktop_dir=desktop_dir,
        desktop_exe=desktop_dir / "Avalonia_UI.exe",
        runtime_dir=runtime_dir,
        log_dir=log_dir,
        token_path=runtime_dir / "config" / "local_api_token",
    )


def validate_portable_layout(
    layout: PortableLayout,
    *,
    no_desktop: bool = False,
) -> None:
    missing = [
        path
        for path in (
            layout.python_exe,
            layout.app_module_path,
        )
        if not path.is_file()
    ]
    if not no_desktop and not layout.desktop_exe.is_file():
        missing.append(layout.desktop_exe)
    if missing:
        formatted = ", ".join(str(path) for path in missing)
        raise LauncherConfigurationError(
            f"Portable layout is incomplete. Missing: {formatted}"
        )


def build_base_url(settings: LauncherSettings) -> str:
    return f"http://{settings.host}:{settings.port}"


def build_enginehost_launch_spec(
    layout: PortableLayout,
    settings: LauncherSettings,
) -> EngineHostLaunchSpec:
    return EngineHostLaunchSpec(
        command=(
            str(layout.python_exe),
            "-m",
            "uvicorn",
            "--app-dir",
            "src",
            APP_IMPORT_TARGET,
            "--factory",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
        ),
        cwd=layout.enginehost_dir,
        stdout_path=layout.log_dir / "enginehost.stdout.log",
        stderr_path=layout.log_dir / "enginehost.stderr.log",
    )


def build_desktop_launch_spec(layout: PortableLayout) -> DesktopLaunchSpec:
    return DesktopLaunchSpec(
        command=(str(layout.desktop_exe),),
        cwd=layout.desktop_dir,
        stdout_path=layout.log_dir / "desktop.stdout.log",
        stderr_path=layout.log_dir / "desktop.stderr.log",
    )


def build_launch_plan(
    portable_root: Path,
    settings: LauncherSettings,
) -> PortableLaunchPlan:
    layout = resolve_portable_layout(portable_root)
    validate_portable_layout(layout, no_desktop=settings.no_desktop)
    desktop = None if settings.no_desktop else build_desktop_launch_spec(layout)
    return PortableLaunchPlan(
        settings=settings,
        layout=layout,
        base_url=build_base_url(settings),
        enginehost=build_enginehost_launch_spec(layout, settings),
        desktop=desktop,
    )


def read_local_api_token(token_path: Path) -> str:
    try:
        token = token_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise LauncherConfigurationError(
            f"Local API token file was not found: {token_path}"
        ) from exc
    if not token:
        raise LauncherConfigurationError(
            f"Local API token file was empty: {token_path}"
        )
    return token


def wait_for_local_api_token(
    token_path: Path,
    process: PollableProcess,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float = 0.2,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_error: LauncherConfigurationError | None = None
    while time.monotonic() < deadline:
        ensure_process_running(process, "EngineHost exited before token was ready")
        try:
            return read_local_api_token(token_path)
        except LauncherConfigurationError as exc:
            last_error = exc
        time.sleep(poll_interval_seconds)
    raise LauncherRuntimeError(
        "Timed out waiting for local API token. "
        + (str(last_error) if last_error is not None else "")
    )


def redact_sensitive_text(text: str, *, token: str | None = None) -> str:
    redacted = re.sub(r"([?&]token=)[^&\s]+", r"\1***", text)
    if token:
        redacted = redacted.replace(token, "***")
    return redacted


def append_launcher_log(
    layout: PortableLayout,
    message: str,
    *,
    token: str | None = None,
) -> None:
    layout.log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat()
    log_line = redact_sensitive_text(f"{timestamp} {message}", token=token)
    launcher_log_path(layout).open("a", encoding="utf-8").write(f"{log_line}\n")


def launcher_log_path(layout: PortableLayout) -> Path:
    return layout.log_dir / "portable-launcher.log"


def ensure_port_available(host: str, port: int) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
    except OSError as exc:
        raise LauncherRuntimeError(
            f"EngineHost port is not available: {host}:{port}"
        ) from exc


def start_enginehost_process(spec: EngineHostLaunchSpec) -> subprocess.Popen[bytes]:
    spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_file = spec.stdout_path.open("ab")
    stderr_file = spec.stderr_path.open("ab")
    try:
        return subprocess.Popen(
            spec.command,
            cwd=spec.cwd,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            **process_group_popen_kwargs(),
        )
    finally:
        stdout_file.close()
        stderr_file.close()


def start_desktop_process(spec: DesktopLaunchSpec) -> subprocess.Popen[bytes]:
    spec.stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_file = spec.stdout_path.open("ab")
    stderr_file = spec.stderr_path.open("ab")
    try:
        try:
            return subprocess.Popen(
                spec.command,
                cwd=spec.cwd,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                **process_group_popen_kwargs(),
            )
        except OSError as exc:
            raise LauncherRuntimeError(f"Failed to start Desktop: {exc}") from exc
    finally:
        stdout_file.close()
        stderr_file.close()


def process_group_popen_kwargs() -> dict[str, object]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def enginehost_health_is_ok(base_url: str, *, timeout_seconds: float = 1.0) -> bool:
    url = f"{base_url.rstrip('/')}/api/v1/health"
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            if response.status != 200:
                return False
            body = response.read().decode("utf-8")
    except (OSError, TimeoutError, URLError):
        return False
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return (
        payload.get("ok") is True
        and isinstance(payload.get("data"), dict)
        and payload["data"].get("status") == "ok"
    )


def wait_for_enginehost_health(
    base_url: str,
    process: PollableProcess,
    *,
    timeout_seconds: float,
    poll_interval_seconds: float = 0.2,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        ensure_process_running(process, "EngineHost exited before health was ready")
        if enginehost_health_is_ok(base_url):
            return
        time.sleep(poll_interval_seconds)
    raise LauncherRuntimeError("Timed out waiting for EngineHost health")


def ensure_process_running(process: PollableProcess, message: str) -> None:
    exit_code = process.poll()
    if exit_code is not None:
        raise LauncherRuntimeError(f"{message}. Exit code: {exit_code}")


def stop_process(process: PollableProcess, *, timeout_seconds: float = 5.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout_seconds)


def wait_for_desktop_exit(
    enginehost_process: PollableProcess,
    desktop_process: PollableProcess,
    *,
    poll_interval_seconds: float = 0.5,
) -> int:
    while True:
        desktop_exit_code = desktop_process.poll()
        if desktop_exit_code is not None:
            return desktop_exit_code
        enginehost_exit_code = enginehost_process.poll()
        if enginehost_exit_code is not None:
            raise LauncherRuntimeError(
                "EngineHost exited while Desktop was running. "
                f"Exit code: {enginehost_exit_code}"
            )
        time.sleep(poll_interval_seconds)


def handle_interrupt_signal(signum: int, frame: object) -> None:
    raise KeyboardInterrupt


def install_launcher_signal_handlers() -> None:
    signal.signal(signal.SIGINT, handle_interrupt_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handle_interrupt_signal)


def run_launch_plan(plan: PortableLaunchPlan) -> int:
    append_launcher_log(plan.layout, f"Starting EngineHost at {plan.base_url}")
    ensure_port_available(plan.settings.host, plan.settings.port)
    enginehost_process = start_enginehost_process(plan.enginehost)
    desktop_process: PollableProcess | None = None
    should_stop_enginehost = True
    token: str | None = None
    try:
        append_launcher_log(
            plan.layout,
            f"EngineHost pid={enginehost_process.pid} cwd={plan.enginehost.cwd}",
        )
        wait_for_enginehost_health(
            plan.base_url,
            enginehost_process,
            timeout_seconds=plan.settings.health_timeout_seconds,
        )
        token = wait_for_local_api_token(
            plan.layout.token_path,
            enginehost_process,
            timeout_seconds=plan.settings.health_timeout_seconds,
        )
        append_launcher_log(
            plan.layout,
            "EngineHost ready. "
            f"BaseUrl={plan.base_url}; token_file={plan.layout.token_path}",
            token=token,
        )
        print("EngineHost ready.")
        print(f"BaseUrl: {plan.base_url}")
        print(f"Token file: {plan.layout.token_path}")
        if plan.desktop is None:
            print("Press Ctrl+C to stop EngineHost.")
            while enginehost_process.poll() is None:
                time.sleep(0.5)
            return enginehost_process.returncode or 0

        append_launcher_log(
            plan.layout,
            f"Starting Desktop cwd={plan.desktop.cwd}",
            token=token,
        )
        desktop_process = start_desktop_process(plan.desktop)
        append_launcher_log(
            plan.layout,
            f"Desktop pid={desktop_process.pid} cwd={plan.desktop.cwd}",
            token=token,
        )
        print("Desktop started.")
        print("Close Desktop or press Ctrl+C to stop FlowWeaver.")
        desktop_exit_code = wait_for_desktop_exit(
            enginehost_process,
            desktop_process,
        )
        append_launcher_log(
            plan.layout,
            f"Desktop exited. Exit code: {desktop_exit_code}",
            token=token,
        )
        if plan.settings.keep_enginehost_on_desktop_exit:
            should_stop_enginehost = False
        return desktop_exit_code
    except KeyboardInterrupt:
        append_launcher_log(plan.layout, "Launcher interrupted by user", token=token)
        return 130
    except LauncherRuntimeError as exc:
        append_launcher_log(plan.layout, f"Launcher runtime error: {exc}", token=token)
        print(f"FlowWeaver portable launcher runtime error: {exc}", file=sys.stderr)
        return 1
    finally:
        if desktop_process is not None and desktop_process.poll() is None:
            stop_process(desktop_process)
            append_launcher_log(plan.layout, "Desktop stopped", token=token)
        if (
            enginehost_process.poll() is None
            and should_stop_enginehost
        ):
            stop_process(enginehost_process)
            append_launcher_log(plan.layout, "EngineHost stopped", token=token)


def main(argv: Sequence[str] | None = None) -> int:
    configure_console_encoding()
    try:
        install_launcher_signal_handlers()
        settings = parse_launcher_args(argv)
        plan = build_launch_plan(Path(__file__).resolve().parent, settings)
        return run_launch_plan(plan)
    except LauncherConfigurationError as exc:
        print(
            f"FlowWeaver portable launcher configuration error: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

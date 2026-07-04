from __future__ import annotations

import importlib.util
import json
import signal
import socket
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_LAUNCHER = None


def launcher() -> ModuleType:
    global _LAUNCHER
    if _LAUNCHER is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "tools" / "portable_launcher.py"
        spec = importlib.util.spec_from_file_location(
            "flowweaver_portable_launcher",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _LAUNCHER = module
    return _LAUNCHER


def test_parse_launcher_args_defaults_to_loopback_port_and_desktop() -> None:
    settings = launcher().parse_launcher_args([])

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.no_desktop is False
    assert settings.health_timeout_seconds == 30
    assert settings.keep_enginehost_on_desktop_exit is False


def test_parse_launcher_args_accepts_minimal_supported_options() -> None:
    settings = launcher().parse_launcher_args(
        [
            "--host",
            "localhost",
            "--port",
            "8010",
            "--no-desktop",
            "--health-timeout-seconds",
            "5",
            "--keep-enginehost-on-desktop-exit",
        ]
    )

    assert settings.host == "localhost"
    assert settings.port == 8010
    assert settings.no_desktop is True
    assert settings.health_timeout_seconds == 5
    assert settings.keep_enginehost_on_desktop_exit is True


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", ""])
def test_settings_rejects_non_loopback_hosts(host: str) -> None:
    with pytest.raises(launcher().LauncherConfigurationError, match="host must"):
        launcher().LauncherSettings(host=host)


@pytest.mark.parametrize("port", [0, 65536])
def test_settings_rejects_invalid_ports(port: int) -> None:
    with pytest.raises(launcher().LauncherConfigurationError, match="port must"):
        launcher().LauncherSettings(port=port)


def test_settings_rejects_invalid_health_timeout() -> None:
    with pytest.raises(
        launcher().LauncherConfigurationError,
        match="health_timeout_seconds must be at least 1",
    ):
        launcher().LauncherSettings(health_timeout_seconds=0)


def test_resolve_portable_layout_uses_expected_relative_paths(
    tmp_path: Path,
) -> None:
    layout = launcher().resolve_portable_layout(tmp_path / "FlowWeaverPortable")

    assert layout.enginehost_dir == layout.root / "EngineHost"
    assert layout.python_exe == layout.root / "EngineHost" / "python312" / "python.exe"
    assert (
        layout.app_module_path
        == layout.root / "EngineHost" / "src" / "flowweaver" / "api" / "app.py"
    )
    assert layout.desktop_exe == layout.root / "Desktop" / "Avalonia_UI.exe"
    assert layout.token_path == (
        layout.root / "EngineHost" / "runtime" / "config" / "local_api_token"
    )


def test_validate_portable_layout_requires_desktop_by_default(
    tmp_path: Path,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=False)

    with pytest.raises(launcher().LauncherConfigurationError, match="Avalonia_UI.exe"):
        launcher().validate_portable_layout(layout)


def test_validate_portable_layout_allows_missing_desktop_when_disabled(
    tmp_path: Path,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=False)

    launcher().validate_portable_layout(layout, no_desktop=True)


def test_build_launch_plan_constructs_enginehost_and_desktop_specs(
    tmp_path: Path,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=True)
    settings = launcher().LauncherSettings(port=8123)

    plan = launcher().build_launch_plan(layout.root, settings)

    assert plan.base_url == "http://127.0.0.1:8123"
    assert plan.enginehost.cwd == layout.enginehost_dir
    assert plan.enginehost.command == (
        str(layout.python_exe),
        "-m",
        "uvicorn",
        "--app-dir",
        "src",
        "flowweaver.api.app:create_default_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        "8123",
    )
    assert plan.enginehost.stdout_path == (
        layout.log_dir / "enginehost.stdout.log"
    )
    assert plan.enginehost.stderr_path == (
        layout.log_dir / "enginehost.stderr.log"
    )
    assert plan.desktop is not None
    assert plan.desktop.command == (str(layout.desktop_exe),)
    assert plan.desktop.cwd == layout.desktop_dir
    assert plan.desktop.stdout_path == layout.log_dir / "desktop.stdout.log"
    assert plan.desktop.stderr_path == layout.log_dir / "desktop.stderr.log"


def test_build_launch_plan_omits_desktop_when_no_desktop(
    tmp_path: Path,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=False)

    plan = launcher().build_launch_plan(
        layout.root,
        launcher().LauncherSettings(no_desktop=True),
    )

    assert plan.desktop is None


def test_read_local_api_token_strips_whitespace(tmp_path: Path) -> None:
    token_path = tmp_path / "local_api_token"
    token_path.write_text(" secret-token \n", encoding="utf-8")

    assert launcher().read_local_api_token(token_path) == "secret-token"


def test_read_local_api_token_rejects_empty_file(tmp_path: Path) -> None:
    token_path = tmp_path / "local_api_token"
    token_path.write_text(" \n", encoding="utf-8")

    with pytest.raises(launcher().LauncherConfigurationError, match="empty"):
        launcher().read_local_api_token(token_path)


def test_redact_sensitive_text_masks_token_query_and_literal_token() -> None:
    text = (
        "ws://127.0.0.1/ws/v1/events?token=secret-token "
        "Authorization=secret-token"
    )

    assert launcher().redact_sensitive_text(text, token="secret-token") == (
        "ws://127.0.0.1/ws/v1/events?token=*** Authorization=***"
    )


def test_append_launcher_log_redacts_token(tmp_path: Path) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=False)

    launcher().append_launcher_log(
        layout,
        "url=ws://127.0.0.1/ws/v1/events?token=secret-token token=secret-token",
        token="secret-token",
    )

    content = launcher().launcher_log_path(layout).read_text(encoding="utf-8")
    assert "secret-token" not in content
    assert "token=***" in content


def test_ensure_port_available_rejects_bound_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, port = sock.getsockname()

        with pytest.raises(
            launcher().LauncherRuntimeError,
            match="port is not available",
        ):
            launcher().ensure_port_available("127.0.0.1", port)


def test_enginehost_health_is_ok_parses_expected_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {"ok": True, "data": {"status": "ok"}}
            ).encode("utf-8")

    def fake_urlopen(url: str, *, timeout: float):
        assert url == "http://127.0.0.1:8000/api/v1/health"
        assert timeout == 1.0
        return FakeResponse()

    monkeypatch.setattr(launcher(), "urlopen", fake_urlopen)

    assert launcher().enginehost_health_is_ok("http://127.0.0.1:8000")


def test_wait_for_enginehost_health_rejects_exited_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(launcher(), "enginehost_health_is_ok", lambda _: False)

    with pytest.raises(launcher().LauncherRuntimeError, match="Exit code: 7"):
        launcher().wait_for_enginehost_health(
            "http://127.0.0.1:8000",
            FakeProcess(returncode=7),
            timeout_seconds=1,
            poll_interval_seconds=0,
        )


def test_wait_for_local_api_token_rejects_exited_process(tmp_path: Path) -> None:
    token_path = tmp_path / "local_api_token"

    with pytest.raises(launcher().LauncherRuntimeError, match="Exit code: 9"):
        launcher().wait_for_local_api_token(
            token_path,
            FakeProcess(returncode=9),
            timeout_seconds=1,
            poll_interval_seconds=0,
        )


def test_stop_process_terminates_running_process() -> None:
    process = FakeProcess(returncode=None)

    launcher().stop_process(process)

    assert process.terminated is True
    assert process.killed is False


def test_stop_enginehost_process_requests_interrupt_first() -> None:
    process = FakeProcess(returncode=None)

    launcher().stop_enginehost_process(process)

    assert process.signals == [_expected_interrupt_signal()]
    assert process.terminated is False
    assert process.killed is False


def test_stop_enginehost_process_terminates_when_interrupt_times_out() -> None:
    process = InterruptTimeoutProcess(returncode=None)

    launcher().stop_enginehost_process(
        process,
        graceful_timeout_seconds=0,
        force_timeout_seconds=1,
    )

    assert process.signals == [_expected_interrupt_signal()]
    assert process.terminated is True
    assert process.killed is False


def test_handle_interrupt_signal_raises_keyboard_interrupt() -> None:
    with pytest.raises(KeyboardInterrupt):
        launcher().handle_interrupt_signal(2, None)


def test_wait_for_desktop_exit_rejects_enginehost_exit() -> None:
    with pytest.raises(launcher().LauncherRuntimeError, match="EngineHost exited"):
        launcher().wait_for_desktop_exit(
            FakeProcess(returncode=9),
            FakeProcess(returncode=None),
            poll_interval_seconds=0,
        )


def test_run_launch_plan_runs_fake_desktop_and_stops_enginehost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=True)
    plan = launcher().build_launch_plan(layout.root, launcher().LauncherSettings())
    enginehost_process = FakeProcess(returncode=None, pid=101)
    desktop_process = FakeProcess(returncode=0, pid=202)

    monkeypatch.setattr(
        launcher(),
        "start_enginehost_process",
        lambda spec: enginehost_process,
    )
    monkeypatch.setattr(launcher(), "wait_for_enginehost_health", lambda *a, **k: None)
    monkeypatch.setattr(
        launcher(),
        "wait_for_local_api_token",
        lambda *a, **k: "secret-token",
    )
    monkeypatch.setattr(
        launcher(),
        "start_desktop_process",
        lambda spec: desktop_process,
    )
    monkeypatch.setattr(
        launcher(),
        "wait_for_desktop_exit",
        lambda enginehost, desktop: 0,
    )
    monkeypatch.setattr(launcher(), "ensure_port_available", lambda *a, **k: None)

    assert launcher().run_launch_plan(plan) == 0

    assert enginehost_process.signals == [_expected_interrupt_signal()]
    assert enginehost_process.terminated is False
    assert desktop_process.terminated is False
    log_content = launcher().launcher_log_path(layout).read_text(encoding="utf-8")
    assert "Starting Desktop" in log_content
    assert "Desktop exited. Exit code: 0" in log_content
    assert "EngineHost stopped" in log_content
    assert "secret-token" not in log_content


def test_run_launch_plan_keeps_enginehost_after_desktop_exit_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=True)
    plan = launcher().build_launch_plan(
        layout.root,
        launcher().LauncherSettings(keep_enginehost_on_desktop_exit=True),
    )
    enginehost_process = FakeProcess(returncode=None, pid=101)
    desktop_process = FakeProcess(returncode=0, pid=202)

    monkeypatch.setattr(
        launcher(),
        "start_enginehost_process",
        lambda spec: enginehost_process,
    )
    monkeypatch.setattr(launcher(), "wait_for_enginehost_health", lambda *a, **k: None)
    monkeypatch.setattr(
        launcher(),
        "wait_for_local_api_token",
        lambda *a, **k: "secret-token",
    )
    monkeypatch.setattr(
        launcher(),
        "start_desktop_process",
        lambda spec: desktop_process,
    )
    monkeypatch.setattr(
        launcher(),
        "wait_for_desktop_exit",
        lambda enginehost, desktop: 0,
    )
    monkeypatch.setattr(launcher(), "ensure_port_available", lambda *a, **k: None)

    assert launcher().run_launch_plan(plan) == 0

    assert enginehost_process.terminated is False
    assert desktop_process.terminated is False
    log_content = launcher().launcher_log_path(layout).read_text(encoding="utf-8")
    assert "Desktop exited. Exit code: 0" in log_content
    assert "EngineHost stopped" not in log_content


def test_run_launch_plan_stops_enginehost_when_desktop_start_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=True)
    plan = launcher().build_launch_plan(layout.root, launcher().LauncherSettings())
    enginehost_process = FakeProcess(returncode=None, pid=101)

    monkeypatch.setattr(
        launcher(),
        "start_enginehost_process",
        lambda spec: enginehost_process,
    )
    monkeypatch.setattr(launcher(), "wait_for_enginehost_health", lambda *a, **k: None)
    monkeypatch.setattr(
        launcher(),
        "wait_for_local_api_token",
        lambda *a, **k: "secret-token",
    )

    def fail_desktop_start(spec):
        raise launcher().LauncherRuntimeError("Failed to start Desktop: fake")

    monkeypatch.setattr(launcher(), "start_desktop_process", fail_desktop_start)
    monkeypatch.setattr(launcher(), "ensure_port_available", lambda *a, **k: None)

    assert launcher().run_launch_plan(plan) == 1
    assert enginehost_process.signals == [_expected_interrupt_signal()]
    assert enginehost_process.terminated is False
    log_content = launcher().launcher_log_path(layout).read_text(encoding="utf-8")
    assert "Launcher runtime error: Failed to start Desktop: fake" in log_content
    assert "EngineHost stopped" in log_content


def test_run_launch_plan_no_desktop_keep_flag_still_stops_on_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout = _create_minimal_layout(tmp_path, include_desktop=False)
    plan = launcher().build_launch_plan(
        layout.root,
        launcher().LauncherSettings(
            no_desktop=True,
            keep_enginehost_on_desktop_exit=True,
        ),
    )
    enginehost_process = InterruptingProcess(returncode=None, pid=101)

    monkeypatch.setattr(
        launcher(),
        "start_enginehost_process",
        lambda spec: enginehost_process,
    )
    monkeypatch.setattr(launcher(), "wait_for_enginehost_health", lambda *a, **k: None)
    monkeypatch.setattr(
        launcher(),
        "wait_for_local_api_token",
        lambda *a, **k: "secret-token",
    )
    monkeypatch.setattr(launcher(), "ensure_port_available", lambda *a, **k: None)

    assert launcher().run_launch_plan(plan) == 130
    assert enginehost_process.signals == [_expected_interrupt_signal()]
    assert enginehost_process.terminated is False
    log_content = launcher().launcher_log_path(layout).read_text(encoding="utf-8")
    assert "Launcher interrupted by user" in log_content
    assert "EngineHost stopped" in log_content


class FakeProcess:
    def __init__(self, *, returncode: int | None, pid: int = 123) -> None:
        self.returncode = returncode
        self.pid = pid
        self.terminated = False
        self.killed = False
        self.signals: list[int] = []

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def send_signal(self, signum: int) -> None:
        self.signals.append(signum)
        self.returncode = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0


class InterruptingProcess(FakeProcess):
    def poll(self) -> int | None:
        if not hasattr(self, "_interrupted"):
            self._interrupted = True
            raise KeyboardInterrupt
        return self.returncode


class InterruptTimeoutProcess(FakeProcess):
    def send_signal(self, signum: int) -> None:
        self.signals.append(signum)

    def wait(self, timeout: float | None = None) -> int:
        if self.terminated or self.killed:
            return super().wait(timeout=timeout)
        raise subprocess.TimeoutExpired("fake", timeout)


def _expected_interrupt_signal() -> int:
    return (
        signal.CTRL_BREAK_EVENT
        if hasattr(signal, "CTRL_BREAK_EVENT")
        else signal.SIGINT
    )


def _create_minimal_layout(
    tmp_path: Path,
    *,
    include_desktop: bool,
):
    root = tmp_path / "FlowWeaverPortable"
    layout = launcher().resolve_portable_layout(root)
    layout.python_exe.parent.mkdir(parents=True)
    layout.python_exe.write_text("", encoding="utf-8")
    layout.app_module_path.parent.mkdir(parents=True)
    layout.app_module_path.write_text("", encoding="utf-8")
    if include_desktop:
        layout.desktop_exe.parent.mkdir(parents=True)
        layout.desktop_exe.write_text("", encoding="utf-8")
    return layout

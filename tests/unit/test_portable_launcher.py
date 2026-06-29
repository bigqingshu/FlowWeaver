from __future__ import annotations

import importlib.util
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

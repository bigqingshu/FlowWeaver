from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_HEALTH_TIMEOUT_SECONDS = 30
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost"})
APP_IMPORT_TARGET = "flowweaver.api.app:create_default_app"


class LauncherConfigurationError(ValueError):
    """Raised when the portable launcher configuration is invalid."""


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


def redact_sensitive_text(text: str, *, token: str | None = None) -> str:
    redacted = re.sub(r"([?&]token=)[^&\s]+", r"\1***", text)
    if token:
        redacted = redacted.replace(token, "***")
    return redacted


def main(argv: Sequence[str] | None = None) -> int:
    try:
        settings = parse_launcher_args(argv)
        plan = build_launch_plan(Path(__file__).resolve().parent, settings)
    except LauncherConfigurationError as exc:
        print(
            f"FlowWeaver portable launcher configuration error: {exc}",
            file=sys.stderr,
        )
        return 2
    print("FlowWeaver portable launcher plan is valid.")
    print(f"BaseUrl: {plan.base_url}")
    print("Process startup is implemented in a later stage.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

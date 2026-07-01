from __future__ import annotations

import argparse
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "FlowWeaverPortable"


def create_portable_layout(
    *,
    repo_root: Path = REPO_ROOT,
    output_dir: Path = DEFAULT_OUTPUT,
    include_python: bool = True,
    include_desktop_build: bool = True,
    clean: bool = True,
) -> Path:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    _validate_output_dir(repo_root=repo_root, output_dir=output_dir)

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)

    enginehost_dir = output_dir / "EngineHost"
    desktop_dir = output_dir / "Desktop"
    docs_dir = output_dir / "docs"
    enginehost_dir.mkdir(parents=True, exist_ok=True)
    desktop_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    _copy_file(repo_root / "alembic.ini", enginehost_dir / "alembic.ini")
    _copy_file(repo_root / "pyproject.toml", enginehost_dir / "pyproject.toml")
    _copy_file(repo_root / "uv.lock", enginehost_dir / "uv.lock")
    _copy_tree(repo_root / "migrations", enginehost_dir / "migrations")
    _copy_tree(repo_root / "src", enginehost_dir / "src")
    _copy_file(
        repo_root / "tools" / "portable_launcher.py",
        output_dir / "portable_launcher.py",
    )
    _write_start_cmd(output_dir / "start_flowweaver.cmd")
    _write_start_desktop_cmd(output_dir / "start_flowweaver_desktop.cmd")
    _write_readme(output_dir / "docs" / "README.txt")
    _copy_file(
        repo_root / "docs" / "FlowWeaver_便携版用户手册.md",
        output_dir / "docs" / "FlowWeaver_便携版用户手册.md",
    )

    if include_python:
        _copy_tree(repo_root / "python312", enginehost_dir / "python312")

    if include_desktop_build:
        _copy_desktop_build(repo_root=repo_root, desktop_dir=desktop_dir)

    return output_dir


def _validate_output_dir(*, repo_root: Path, output_dir: Path) -> None:
    tmp_root = (repo_root / ".tmp").resolve()
    if output_dir != tmp_root and tmp_root in output_dir.parents:
        return
    raise ValueError(f"output_dir must be a child directory inside {tmp_root}")


def _copy_file(source: Path, target: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)


def _copy_desktop_build(*, repo_root: Path, desktop_dir: Path) -> None:
    release_dir = (
        repo_root
        / "Avalonia_UI"
        / "bin"
        / "Release"
        / "net10.0"
        / "win-x64"
        / "publish"
    )
    debug_dir = repo_root / "Avalonia_UI" / "bin" / "Debug" / "net10.0"
    source_dir = release_dir if release_dir.is_dir() else debug_dir
    if not source_dir.is_dir():
        return
    _copy_tree(source_dir, desktop_dir)


def _write_start_cmd(path: Path) -> None:
    path.write_text(
        "\r\n".join(
            [
                "@echo off",
                "setlocal",
                'cd /d "%~dp0"',
                (
                    '"EngineHost\\python312\\python.exe" '
                    '"portable_launcher.py" --no-desktop %*'
                ),
                "exit /b %ERRORLEVEL%",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_start_desktop_cmd(path: Path) -> None:
    path.write_text(
        "\r\n".join(
            [
                "@echo off",
                "setlocal",
                'cd /d "%~dp0"',
                (
                    '"EngineHost\\python312\\python.exe" '
                    '"portable_launcher.py" %*'
                ),
                "exit /b %ERRORLEVEL%",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_readme(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "FlowWeaver Portable Layout",
                "",
                "Start the backend-only launcher on Windows:",
                "start_flowweaver.cmd",
                "",
                "Backend-only equivalent command:",
                "EngineHost/python312/python.exe portable_launcher.py --no-desktop",
                "",
                "Start the Desktop combo launcher on Windows:",
                "start_flowweaver_desktop.cmd",
                "",
                "Desktop combo equivalent command:",
                "EngineHost/python312/python.exe portable_launcher.py",
                "",
                "Optional launcher arguments can be passed through both cmd wrappers.",
                "",
                "Full portable user manual:",
                "docs/FlowWeaver_便携版用户手册.md",
                "Backend-only example:",
                "start_flowweaver.cmd --port 8000 --health-timeout-seconds 30",
                "Desktop combo example:",
                (
                    "start_flowweaver_desktop.cmd --port 8000 "
                    "--health-timeout-seconds 30"
                ),
                "",
                "Default EngineHost BaseUrl: http://127.0.0.1:8000",
                "Local API token is generated at:",
                "EngineHost/runtime/config/local_api_token.",
                "Launcher and EngineHost logs are generated under:",
                "EngineHost/runtime/logs.",
                "Do not log or share the token value.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a FlowWeaver portable dual-process layout."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory. Must be inside repo .tmp/.",
    )
    parser.add_argument(
        "--no-python",
        action="store_true",
        help="Skip copying repo-local python312 runtime.",
    )
    parser.add_argument(
        "--no-desktop-build",
        action="store_true",
        help="Skip copying existing Avalonia build output.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete the output directory before copying.",
    )
    args = parser.parse_args()
    output_dir = create_portable_layout(
        output_dir=args.output,
        include_python=not args.no_python,
        include_desktop_build=not args.no_desktop_build,
        clean=not args.no_clean,
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

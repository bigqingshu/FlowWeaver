from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PYTHON = REPO_ROOT / "python312"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "FlowWeaverReleasePython312"
KEEP_TOOLING_PACKAGES = frozenset({"pip"})
CommandRunner = Callable[[Sequence[str]], None]


class ReleasePythonRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleasePythonRuntimeResult:
    output_dir: Path
    source_python_dir: Path
    requirements: tuple[str, ...]
    kept_tooling_packages: tuple[str, ...]
    install_dependencies: bool


def create_release_python_runtime(
    *,
    repo_root: Path = REPO_ROOT,
    source_python_dir: Path = DEFAULT_SOURCE_PYTHON,
    output_dir: Path = DEFAULT_OUTPUT,
    clean: bool = True,
    install_dependencies: bool = True,
    command_runner: CommandRunner | None = None,
) -> ReleasePythonRuntimeResult:
    repo_root = repo_root.resolve()
    source_python_dir = _resolve_path(source_python_dir, base=repo_root)
    output_dir = _resolve_path(output_dir, base=repo_root)
    _validate_output_dir(repo_root=repo_root, output_dir=output_dir)
    _validate_source_python_dir(source_python_dir)
    if source_python_dir == output_dir:
        raise ReleasePythonRuntimeError("output_dir must differ from source_python_dir")

    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    if output_dir.exists():
        raise ReleasePythonRuntimeError(
            f"output directory already exists: {output_dir}"
        )

    shutil.copytree(
        source_python_dir,
        output_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    _prepare_release_site_packages(
        source_site_packages=source_python_dir / "Lib" / "site-packages",
        output_site_packages=output_dir / "Lib" / "site-packages",
    )
    requirements = tuple(_read_runtime_requirements(repo_root / "pyproject.toml"))
    if install_dependencies and requirements:
        runner = command_runner or _run_command
        runner(
            (
                str(output_dir / "python.exe"),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--upgrade",
                *requirements,
            )
        )
    _remove_python_caches(output_dir)
    return ReleasePythonRuntimeResult(
        output_dir=output_dir,
        source_python_dir=source_python_dir,
        requirements=requirements,
        kept_tooling_packages=tuple(sorted(KEEP_TOOLING_PACKAGES)),
        install_dependencies=install_dependencies,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a clean FlowWeaver release Python 3.12 runtime."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_PYTHON,
        help="Source embedded Python directory. Defaults to repo python312.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory. Must be inside repo .tmp/.",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete a previous output directory first.",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="Only copy the Python base and pip; skip runtime dependency install.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_release_python_runtime(
            source_python_dir=args.source,
            output_dir=args.output,
            clean=not args.no_clean,
            install_dependencies=not args.no_install,
        )
    except ReleasePythonRuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(result.output_dir)
    return 0


def _resolve_path(path: Path, *, base: Path) -> Path:
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _validate_output_dir(*, repo_root: Path, output_dir: Path) -> None:
    tmp_root = (repo_root / ".tmp").resolve()
    if output_dir != tmp_root and tmp_root in output_dir.parents:
        return
    raise ReleasePythonRuntimeError(f"output_dir must be inside {tmp_root}")


def _validate_source_python_dir(source_python_dir: Path) -> None:
    required_files = (
        "python.exe",
        "python312._pth",
        "LICENSE.txt",
    )
    if not source_python_dir.is_dir():
        raise ReleasePythonRuntimeError(
            f"source Python directory does not exist: {source_python_dir}"
        )
    for file_name in required_files:
        if not (source_python_dir / file_name).is_file():
            raise ReleasePythonRuntimeError(
                f"source Python runtime missing required file: {file_name}"
            )
    if "import site" not in (source_python_dir / "python312._pth").read_text(
        encoding="utf-8"
    ):
        raise ReleasePythonRuntimeError("source python312._pth must enable import site")
    if not (source_python_dir / "Lib" / "site-packages").is_dir():
        raise ReleasePythonRuntimeError("source Python runtime missing site-packages")


def _prepare_release_site_packages(
    *,
    source_site_packages: Path,
    output_site_packages: Path,
) -> None:
    if output_site_packages.exists():
        shutil.rmtree(output_site_packages)
    output_site_packages.mkdir(parents=True)
    for child in source_site_packages.iterdir():
        if not _is_kept_tooling_child(child):
            continue
        target = output_site_packages / child.name
        if child.is_dir():
            shutil.copytree(
                child,
                target,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        elif child.is_file():
            shutil.copy2(child, target)


def _is_kept_tooling_child(path: Path) -> bool:
    name = path.name.lower()
    if name == "pip":
        return True
    if name.startswith("pip-") and name.endswith(".dist-info"):
        return True
    return False


def _read_runtime_requirements(pyproject_path: Path) -> list[str]:
    if not pyproject_path.is_file():
        raise ReleasePythonRuntimeError(f"pyproject.toml missing: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependencies = data.get("project", {}).get("dependencies")
    if not isinstance(dependencies, list):
        raise ReleasePythonRuntimeError(
            "pyproject.toml project.dependencies is required"
        )
    requirements: list[str] = []
    for dependency in dependencies:
        if not isinstance(dependency, str) or not dependency:
            raise ReleasePythonRuntimeError("project.dependencies must contain strings")
        requirements.append(dependency)
    return requirements


def _remove_python_caches(root: Path) -> None:
    for cache_dir in sorted(root.rglob("__pycache__"), reverse=True):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
    for pyc_file in root.rglob("*.pyc"):
        if pyc_file.is_file():
            pyc_file.unlink()


def _run_command(command: Sequence[str]) -> None:
    subprocess.run(list(command), check=True)


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import re
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
DEFAULT_LOCK_FILE = REPO_ROOT / "uv.lock"
KEEP_TOOLING_PACKAGES = frozenset({"pip"})
CommandRunner = Callable[[Sequence[str]], None]
DEPENDENCY_SOURCE_PYPROJECT = "pyproject"
DEPENDENCY_SOURCE_LOCK = "lock"


class ReleasePythonRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleasePythonRuntimeResult:
    output_dir: Path
    source_python_dir: Path
    requirements: tuple[str, ...]
    kept_tooling_packages: tuple[str, ...]
    install_dependencies: bool
    dependency_source: str
    lock_file: Path | None


def create_release_python_runtime(
    *,
    repo_root: Path = REPO_ROOT,
    source_python_dir: Path = DEFAULT_SOURCE_PYTHON,
    output_dir: Path = DEFAULT_OUTPUT,
    dependency_source: str = DEPENDENCY_SOURCE_PYPROJECT,
    lock_file: Path | None = None,
    clean: bool = True,
    install_dependencies: bool = True,
    command_runner: CommandRunner | None = None,
) -> ReleasePythonRuntimeResult:
    repo_root = repo_root.resolve()
    source_python_dir = _resolve_path(source_python_dir, base=repo_root)
    output_dir = _resolve_path(output_dir, base=repo_root)
    resolved_lock_file = (
        _resolve_path(lock_file, base=repo_root)
        if lock_file is not None
        else repo_root / "uv.lock"
    )
    _validate_output_dir(repo_root=repo_root, output_dir=output_dir)
    _validate_source_python_dir(source_python_dir)
    _validate_dependency_source(dependency_source)
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
    requirements = tuple(
        _read_runtime_requirements(
            repo_root=repo_root,
            dependency_source=dependency_source,
            lock_file=resolved_lock_file,
        )
    )
    if install_dependencies and requirements:
        runner = command_runner or _run_command
        if dependency_source == DEPENDENCY_SOURCE_LOCK:
            _install_locked_requirements(
                output_dir=output_dir,
                requirements=requirements,
                runner=runner,
            )
        else:
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
        dependency_source=dependency_source,
        lock_file=(
            resolved_lock_file
            if dependency_source == DEPENDENCY_SOURCE_LOCK
            else None
        ),
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
    parser.add_argument(
        "--locked",
        action="store_true",
        help="Install runtime dependencies from uv.lock with hashes.",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=DEFAULT_LOCK_FILE,
        help="Lock file used with --locked. Defaults to repo uv.lock.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_release_python_runtime(
            source_python_dir=args.source,
            output_dir=args.output,
            dependency_source=DEPENDENCY_SOURCE_LOCK
            if args.locked
            else DEPENDENCY_SOURCE_PYPROJECT,
            lock_file=args.lock_file,
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


def _validate_dependency_source(dependency_source: str) -> None:
    if dependency_source not in {
        DEPENDENCY_SOURCE_PYPROJECT,
        DEPENDENCY_SOURCE_LOCK,
    }:
        raise ReleasePythonRuntimeError(
            "dependency_source must be 'pyproject' or 'lock'"
        )


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


def _read_runtime_requirements(
    *,
    repo_root: Path,
    dependency_source: str,
    lock_file: Path,
) -> list[str]:
    if dependency_source == DEPENDENCY_SOURCE_LOCK:
        return _read_locked_runtime_requirements(
            pyproject_path=repo_root / "pyproject.toml",
            lock_file=_resolve_path(lock_file, base=repo_root),
        )
    return _read_pyproject_runtime_requirements(repo_root / "pyproject.toml")


def _read_pyproject_runtime_requirements(pyproject_path: Path) -> list[str]:
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


def _read_locked_runtime_requirements(
    *,
    pyproject_path: Path,
    lock_file: Path,
) -> list[str]:
    project_name = _read_project_name(pyproject_path)
    if not lock_file.is_file():
        raise ReleasePythonRuntimeError(f"lock file missing: {lock_file}")
    data = tomllib.loads(lock_file.read_text(encoding="utf-8"))
    packages = data.get("package")
    if not isinstance(packages, list):
        raise ReleasePythonRuntimeError("uv.lock package list is required")

    packages_by_name = _packages_by_normalized_name(packages)
    root_name = _normalize_package_name(project_name)
    root_package = packages_by_name.get(root_name)
    if root_package is None:
        raise ReleasePythonRuntimeError(
            f"uv.lock missing project package: {project_name}"
        )

    required_names = _runtime_dependency_closure(
        root_package=root_package,
        packages_by_name=packages_by_name,
        root_name=root_name,
    )
    return [
        _locked_requirement_line(packages_by_name[name])
        for name in sorted(required_names)
    ]


def _read_project_name(pyproject_path: Path) -> str:
    if not pyproject_path.is_file():
        raise ReleasePythonRuntimeError(f"pyproject.toml missing: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project_name = data.get("project", {}).get("name")
    if not isinstance(project_name, str) or not project_name:
        raise ReleasePythonRuntimeError("pyproject.toml project.name is required")
    return project_name


def _packages_by_normalized_name(
    packages: Sequence[object],
) -> dict[str, dict[str, object]]:
    packages_by_name: dict[str, dict[str, object]] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise ReleasePythonRuntimeError("uv.lock packages must be tables")
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not name:
            raise ReleasePythonRuntimeError("uv.lock package.name is required")
        if not isinstance(version, str) or not version:
            raise ReleasePythonRuntimeError(f"uv.lock package {name!r} missing version")
        normalized = _normalize_package_name(name)
        if normalized in packages_by_name:
            raise ReleasePythonRuntimeError(
                f"uv.lock contains duplicate package name: {name}"
            )
        packages_by_name[normalized] = package
    return packages_by_name


def _runtime_dependency_closure(
    *,
    root_package: dict[str, object],
    packages_by_name: dict[str, dict[str, object]],
    root_name: str,
) -> set[str]:
    required_names: set[str] = set()
    pending = list(_dependency_names(root_package))
    while pending:
        dependency_name = pending.pop()
        normalized = _normalize_package_name(dependency_name)
        if normalized == root_name or normalized in required_names:
            continue
        package = packages_by_name.get(normalized)
        if package is None:
            raise ReleasePythonRuntimeError(
                f"uv.lock missing dependency package: {dependency_name}"
            )
        required_names.add(normalized)
        pending.extend(_dependency_names(package))
    return required_names


def _dependency_names(package: dict[str, object]) -> tuple[str, ...]:
    dependencies = package.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise ReleasePythonRuntimeError("uv.lock package.dependencies must be a list")
    names: list[str] = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise ReleasePythonRuntimeError("uv.lock dependencies must be tables")
        name = dependency.get("name")
        if not isinstance(name, str) or not name:
            raise ReleasePythonRuntimeError("uv.lock dependency.name is required")
        names.append(name)
    return tuple(names)


def _locked_requirement_line(package: dict[str, object]) -> str:
    name = package["name"]
    version = package["version"]
    hashes = sorted(_wheel_hashes(package))
    if not hashes:
        raise ReleasePythonRuntimeError(
            f"uv.lock package {name!r} has no wheel hashes"
        )
    hash_options = " ".join(f"--hash={package_hash}" for package_hash in hashes)
    return f"{name}=={version} {hash_options}"


def _wheel_hashes(package: dict[str, object]) -> set[str]:
    wheels = package.get("wheels")
    if not isinstance(wheels, list):
        return set()
    hashes: set[str] = set()
    for wheel in wheels:
        if not isinstance(wheel, dict):
            continue
        package_hash = wheel.get("hash")
        if isinstance(package_hash, str) and package_hash.startswith("sha256:"):
            hashes.add(package_hash)
    return hashes


def _install_locked_requirements(
    *,
    output_dir: Path,
    requirements: Sequence[str],
    runner: CommandRunner,
) -> None:
    requirements_path = output_dir.parent / f"{output_dir.name}-requirements.lock.txt"
    requirements_path.write_text(
        "\n".join(
            [
                "# Generated from uv.lock for FlowWeaver release runtime.",
                "# This file is transient and is not copied into the runtime.",
                *requirements,
                "",
            ]
        ),
        encoding="utf-8",
    )
    try:
        runner(
            (
                str(output_dir / "python.exe"),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-warn-script-location",
                "--upgrade",
                "--require-hashes",
                "--only-binary=:all:",
                "-r",
                str(requirements_path),
            )
        )
    finally:
        if requirements_path.exists():
            requirements_path.unlink()


def _remove_python_caches(root: Path) -> None:
    for cache_dir in sorted(root.rglob("__pycache__"), reverse=True):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
    for pyc_file in root.rglob("*.pyc"):
        if pyc_file.is_file():
            pyc_file.unlink()


def _run_command(command: Sequence[str]) -> None:
    subprocess.run(list(command), check=True)


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


if __name__ == "__main__":
    raise SystemExit(main())

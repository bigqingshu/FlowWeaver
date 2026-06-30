from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

AuditStatus = Literal["checked", "warning", "rejected", "unchecked"]
CommandRunner = Callable[[Sequence[str]], str]

DEFAULT_PORTABLE_ROOT = Path(__file__).resolve().parents[1] / ".tmp" / (
    "FlowWeaverPortable"
)
PYTHON_VERSION_PATTERN = re.compile(r"Python\s+(?P<version>\d+\.\d+(?:\.\d+)?)")
PIP_VERSION_PATTERN = re.compile(r"\bpip\s+(?P<version>[^\s]+)")
DIST_INFO_SUFFIX = ".dist-info"

DEV_OR_LEGACY_PACKAGE_NAMES = frozenset(
    {
        "coverage",
        "hatchling",
        "mypy",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-qt",
        "pytest-timeout",
        "pyside6",
        "pyside6-addons",
        "pyside6-essentials",
        "ruff",
        "shiboken6",
    }
)
REJECTED_DIRECTORY_NAMES = frozenset({".git", ".tmp", ".venv", ".pytest_cache"})
REJECTED_RUNTIME_DIRS = frozenset({"EngineHost/runtime", "Desktop/runtime"})
REJECTED_FILE_NAMES = frozenset(
    {
        "flowweaver.db",
        "local_api_token",
        "portable-launcher.log",
    }
)
REJECTED_FILE_SUFFIXES = (".stdout.log", ".stderr.log")
EXCLUDED_DIRECTORY_NAMES = frozenset({"__pycache__"})
EXCLUDED_FILE_SUFFIXES = (".pyc",)


@dataclass(frozen=True)
class RuntimeAuditIssue:
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class RuntimePackage:
    name: str
    version: str
    path: str


@dataclass(frozen=True)
class RuntimeAuditResult:
    status: AuditStatus
    python_version: str | None
    pip_version: str | None
    errors: tuple[RuntimeAuditIssue, ...]
    warnings: tuple[RuntimeAuditIssue, ...]
    rejected_paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    packages: tuple[RuntimePackage, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "python_version": self.python_version,
            "pip_version": self.pip_version,
            "errors": [asdict(error) for error in self.errors],
            "warnings": [asdict(warning) for warning in self.warnings],
            "rejected_paths": list(self.rejected_paths),
            "excluded_paths": list(self.excluded_paths),
            "packages": [asdict(package) for package in self.packages],
        }


def audit_portable_runtime(
    portable_root: Path,
    *,
    command_runner: CommandRunner | None = None,
    runtime_audit_mode: Literal["strict"] = "strict",
) -> RuntimeAuditResult:
    if runtime_audit_mode != "strict":
        raise ValueError("runtime_audit_mode currently only supports 'strict'")

    portable_root = portable_root.resolve()
    command_runner = command_runner or run_command
    errors: list[RuntimeAuditIssue] = []
    warnings: list[RuntimeAuditIssue] = []
    rejected_paths: set[str] = set()
    excluded_paths: set[str] = set()

    if not portable_root.is_dir():
        errors.append(
            RuntimeAuditIssue(
                code="portable_root_missing",
                message="portable root directory does not exist",
                path=str(portable_root),
            )
        )
        return _build_result(
            python_version=None,
            pip_version=None,
            errors=errors,
            warnings=warnings,
            rejected_paths=rejected_paths,
            excluded_paths=excluded_paths,
            packages=[],
        )

    python_dir = portable_root / "EngineHost" / "python312"
    python_exe = python_dir / "python.exe"
    pth_path = python_dir / "python312._pth"
    license_path = python_dir / "LICENSE.txt"

    _collect_path_findings(
        portable_root=portable_root,
        rejected_paths=rejected_paths,
        excluded_paths=excluded_paths,
    )
    for relative_path in sorted(rejected_paths):
        errors.append(
            RuntimeAuditIssue(
                code="rejected_path_present",
                message="portable runtime contains a path that must not be archived",
                path=relative_path,
            )
        )
    if excluded_paths:
        warnings.append(
            RuntimeAuditIssue(
                code="excluded_cache_paths_present",
                message="portable runtime contains cache paths that must be excluded",
            )
        )

    if not python_exe.is_file():
        errors.append(
            RuntimeAuditIssue(
                code="python_exe_missing",
                message="EngineHost/python312/python.exe is required",
                path=_relative_posix(python_exe, portable_root),
            )
        )
        python_version = None
        pip_version = None
    else:
        python_version = _read_python_version(
            python_exe=python_exe,
            command_runner=command_runner,
            errors=errors,
        )
        pip_version = _read_pip_version(
            python_exe=python_exe,
            command_runner=command_runner,
            warnings=warnings,
        )

    if not pth_path.is_file():
        errors.append(
            RuntimeAuditIssue(
                code="python_pth_missing",
                message="python312._pth is required for embedded Python audit",
                path=_relative_posix(pth_path, portable_root),
            )
        )
    elif not _pth_import_site_enabled(pth_path):
        errors.append(
            RuntimeAuditIssue(
                code="python_site_disabled",
                message="python312._pth must enable import site",
                path=_relative_posix(pth_path, portable_root),
            )
        )

    if not license_path.is_file():
        errors.append(
            RuntimeAuditIssue(
                code="python_license_missing",
                message="Python LICENSE.txt is required for distributable runtime",
                path=_relative_posix(license_path, portable_root),
            )
        )

    packages = _discover_packages(
        site_packages_dir=python_dir / "Lib" / "site-packages",
        portable_root=portable_root,
    )
    for package in packages:
        if _normalize_package_name(package.name) in DEV_OR_LEGACY_PACKAGE_NAMES:
            warnings.append(
                RuntimeAuditIssue(
                    code="dev_or_legacy_package_present",
                    message=(
                        "dev, test, build, or legacy GUI package is present in "
                        "python312 runtime"
                    ),
                    path=package.path,
                )
            )

    return _build_result(
        python_version=python_version,
        pip_version=pip_version,
        errors=errors,
        warnings=warnings,
        rejected_paths=rejected_paths,
        excluded_paths=excluded_paths,
        packages=packages,
    )


def run_command(command: Sequence[str]) -> str:
    completed = subprocess.run(
        list(command),
        check=True,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or completed.stderr).strip()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a FlowWeaver portable Python runtime before archiving."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_PORTABLE_ROOT,
        help="Portable root directory, usually .tmp/FlowWeaverPortable.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit_portable_runtime(args.input)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result.status == "rejected" else 0


def _read_python_version(
    *,
    python_exe: Path,
    command_runner: CommandRunner,
    errors: list[RuntimeAuditIssue],
) -> str | None:
    try:
        output = command_runner((str(python_exe), "--version"))
    except Exception as exc:  # pragma: no cover - defensive boundary
        errors.append(
            RuntimeAuditIssue(
                code="python_version_unavailable",
                message=f"could not read Python version: {exc}",
                path=str(python_exe),
            )
        )
        return None

    match = PYTHON_VERSION_PATTERN.search(output)
    if match is None:
        errors.append(
            RuntimeAuditIssue(
                code="python_version_unparseable",
                message=f"could not parse Python version from output: {output}",
                path=str(python_exe),
            )
        )
        return None

    version = match.group("version")
    if not version.startswith("3.12."):
        errors.append(
            RuntimeAuditIssue(
                code="python_version_unsupported",
                message=f"expected Python 3.12.x, got {version}",
                path=str(python_exe),
            )
        )
    return version


def _read_pip_version(
    *,
    python_exe: Path,
    command_runner: CommandRunner,
    warnings: list[RuntimeAuditIssue],
) -> str | None:
    try:
        output = command_runner((str(python_exe), "-m", "pip", "--version"))
    except Exception as exc:  # pragma: no cover - defensive boundary
        warnings.append(
            RuntimeAuditIssue(
                code="pip_version_unavailable",
                message=f"could not read pip version: {exc}",
                path=str(python_exe),
            )
        )
        return None

    match = PIP_VERSION_PATTERN.search(output)
    if match is None:
        warnings.append(
            RuntimeAuditIssue(
                code="pip_version_unparseable",
                message=f"could not parse pip version from output: {output}",
                path=str(python_exe),
            )
        )
        return None
    return match.group("version")


def _pth_import_site_enabled(path: Path) -> bool:
    lines = path.read_text(encoding="utf-8").splitlines()
    return any(line.strip() == "import site" for line in lines)


def _discover_packages(
    *,
    site_packages_dir: Path,
    portable_root: Path,
) -> tuple[RuntimePackage, ...]:
    if not site_packages_dir.is_dir():
        return ()

    packages: list[RuntimePackage] = []
    for path in sorted(site_packages_dir.iterdir(), key=lambda item: item.name.lower()):
        if not path.name.endswith(DIST_INFO_SUFFIX):
            continue
        raw = path.name[: -len(DIST_INFO_SUFFIX)]
        if "-" not in raw:
            continue
        name, version = raw.rsplit("-", 1)
        packages.append(
            RuntimePackage(
                name=_normalize_package_name(name),
                version=version,
                path=_relative_posix(path, portable_root),
            )
        )
    return tuple(packages)


def _collect_path_findings(
    *,
    portable_root: Path,
    rejected_paths: set[str],
    excluded_paths: set[str],
) -> None:
    for path in portable_root.rglob("*"):
        relative_path = _relative_posix(path, portable_root)
        relative_lower = relative_path.lower()
        name_lower = path.name.lower()

        if path.is_dir():
            if name_lower in REJECTED_DIRECTORY_NAMES:
                rejected_paths.add(relative_path + "/")
            if name_lower in EXCLUDED_DIRECTORY_NAMES:
                excluded_paths.add(relative_path + "/")
            if relative_path in REJECTED_RUNTIME_DIRS:
                rejected_paths.add(relative_path + "/")
            continue

        if name_lower in REJECTED_FILE_NAMES:
            rejected_paths.add(relative_path)
        if relative_lower.endswith(REJECTED_FILE_SUFFIXES):
            rejected_paths.add(relative_path)
        if relative_lower.endswith(EXCLUDED_FILE_SUFFIXES):
            excluded_paths.add(relative_path)


def _build_result(
    *,
    python_version: str | None,
    pip_version: str | None,
    errors: Sequence[RuntimeAuditIssue],
    warnings: Sequence[RuntimeAuditIssue],
    rejected_paths: set[str],
    excluded_paths: set[str],
    packages: Sequence[RuntimePackage],
) -> RuntimeAuditResult:
    if errors:
        status: AuditStatus = "rejected"
    elif warnings:
        status = "warning"
    else:
        status = "checked"
    return RuntimeAuditResult(
        status=status,
        python_version=python_version,
        pip_version=pip_version,
        errors=tuple(errors),
        warnings=tuple(warnings),
        rejected_paths=tuple(sorted(rejected_paths)),
        excluded_paths=tuple(sorted(excluded_paths)),
        packages=tuple(packages),
    )


def _relative_posix(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


if __name__ == "__main__":
    raise SystemExit(main())

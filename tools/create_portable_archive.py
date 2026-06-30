from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from portable_runtime_audit import (  # noqa: E402
    CommandRunner,
    RuntimeAuditResult,
    audit_portable_runtime,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / ".tmp" / "FlowWeaverPortable"
DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "dist"
ARCHIVE_ROOT_NAME = "FlowWeaverPortable"
SUPPORTED_TARGET_RUNTIME = "win-x64"
SUPPORTED_DESKTOP_PUBLISH_MODE = "framework-dependent"
MANIFEST_ARCHIVE_PATH = f"{ARCHIVE_ROOT_NAME}/release-manifest.json"
LICENSE_DIR_ARCHIVE_PATH = f"{ARCHIVE_ROOT_NAME}/licenses"
FLOWWEAVER_LICENSE_ARCHIVE_PATH = (
    f"{LICENSE_DIR_ARCHIVE_PATH}/FlowWeaver-LICENSE.txt"
)
PYTHON_LICENSE_ARCHIVE_PATH = f"{LICENSE_DIR_ARCHIVE_PATH}/Python-LICENSE.txt"
THIRD_PARTY_LICENSES_ARCHIVE_PATH = (
    f"{LICENSE_DIR_ARCHIVE_PATH}/third-party-licenses.json"
)


class ArchiveConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True)
class PortableArchiveResult:
    archive_path: Path
    sha256_path: Path
    manifest: dict[str, object]
    runtime_audit: RuntimeAuditResult


def create_portable_archive(
    *,
    repo_root: Path = REPO_ROOT,
    input_dir: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT,
    version: str | None = None,
    target_runtime: str = SUPPORTED_TARGET_RUNTIME,
    desktop_publish_mode: str = SUPPORTED_DESKTOP_PUBLISH_MODE,
    command_runner: CommandRunner | None = None,
) -> PortableArchiveResult:
    repo_root = repo_root.resolve()
    input_dir = _resolve_path(input_dir, base=repo_root)
    output_dir = _resolve_path(output_dir, base=repo_root)
    _validate_output_dir(repo_root=repo_root, output_dir=output_dir)
    _validate_input_dir(input_dir)
    _validate_target_runtime(target_runtime)
    _validate_desktop_publish_mode(desktop_publish_mode)

    project_version = _read_python_project_version(repo_root / "pyproject.toml")
    release_version = version or project_version
    if release_version != project_version:
        raise ArchiveConfigurationError(
            f"--version must match pyproject.toml version {project_version!r}"
        )

    runtime_audit = audit_portable_runtime(
        input_dir,
        command_runner=command_runner,
    )
    if runtime_audit.status == "rejected":
        raise ArchiveConfigurationError("runtime audit rejected portable input")

    archive_name = f"{ARCHIVE_ROOT_NAME}-{release_version}-{target_runtime}.zip"
    archive_path = output_dir / archive_name
    sha256_path = output_dir / f"{archive_name}.sha256"
    if archive_path.exists() or sha256_path.exists():
        raise ArchiveConfigurationError(
            f"archive output already exists: {archive_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    file_entries = _collect_input_file_entries(
        input_dir=input_dir,
        excluded_paths=set(runtime_audit.excluded_paths),
    )
    generated_files = _build_generated_files(
        repo_root=repo_root,
        input_dir=input_dir,
        runtime_audit=runtime_audit,
    )
    file_entries.extend(
        ArchiveEntry(
            path=archive_path,
            size=len(content),
            sha256=_sha256_bytes(content),
        )
        for archive_path, content in generated_files.items()
    )
    file_entries.sort(key=lambda entry: entry.path)

    manifest = _build_manifest(
        archive_name=archive_name,
        target_runtime=target_runtime,
        release_version=release_version,
        python_project_version=project_version,
        desktop_project_version=_read_desktop_project_version(
            repo_root / "Avalonia_UI" / "Avalonia_UI.csproj"
        ),
        runtime_audit=runtime_audit,
        entries=file_entries,
        repo_root=repo_root,
    )
    manifest_bytes = _json_bytes(manifest)

    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        _write_input_files(
            archive=archive,
            input_dir=input_dir,
            excluded_paths=set(runtime_audit.excluded_paths),
        )
        for archive_path_in_zip, content in sorted(generated_files.items()):
            archive.writestr(archive_path_in_zip, content)
        archive.writestr(MANIFEST_ARCHIVE_PATH, manifest_bytes)

    archive_sha256 = _sha256_file(archive_path)
    sha256_path.write_text(f"{archive_sha256}  {archive_name}\n", encoding="utf-8")
    return PortableArchiveResult(
        archive_path=archive_path,
        sha256_path=sha256_path,
        manifest=manifest,
        runtime_audit=runtime_audit,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a FlowWeaver portable zip archive."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Portable layout directory, usually .tmp/FlowWeaverPortable.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory. Must be inside repo .tmp/.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Release version. If provided, must match pyproject.toml.",
    )
    parser.add_argument(
        "--target-runtime",
        default=SUPPORTED_TARGET_RUNTIME,
        help="Archive target runtime. P.3 supports win-x64 only.",
    )
    parser.add_argument(
        "--desktop-publish-mode",
        default=SUPPORTED_DESKTOP_PUBLISH_MODE,
        choices=[SUPPORTED_DESKTOP_PUBLISH_MODE, "self-contained"],
        help="Desktop publish mode. P.3 supports framework-dependent only.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = create_portable_archive(
            input_dir=args.input,
            output_dir=args.output,
            version=args.version,
            target_runtime=args.target_runtime,
            desktop_publish_mode=args.desktop_publish_mode,
        )
    except ArchiveConfigurationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "archive_path": str(result.archive_path),
                "sha256_path": str(result.sha256_path),
                "runtime_audit_status": result.runtime_audit.status,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _resolve_path(path: Path, *, base: Path) -> Path:
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def _validate_output_dir(*, repo_root: Path, output_dir: Path) -> None:
    tmp_root = (repo_root / ".tmp").resolve()
    if output_dir == tmp_root or tmp_root in output_dir.parents:
        return
    raise ArchiveConfigurationError(f"output_dir must be inside {tmp_root}")


def _validate_input_dir(input_dir: Path) -> None:
    if not input_dir.is_dir():
        raise ArchiveConfigurationError(f"input directory does not exist: {input_dir}")
    if (input_dir / "release-manifest.json").exists():
        raise ArchiveConfigurationError("input directory contains stale manifest")
    if (input_dir / "licenses").exists():
        raise ArchiveConfigurationError("input directory contains stale licenses")


def _validate_target_runtime(target_runtime: str) -> None:
    if target_runtime != SUPPORTED_TARGET_RUNTIME:
        raise ArchiveConfigurationError(
            f"target runtime must be {SUPPORTED_TARGET_RUNTIME!r}"
        )


def _validate_desktop_publish_mode(desktop_publish_mode: str) -> None:
    if desktop_publish_mode != SUPPORTED_DESKTOP_PUBLISH_MODE:
        raise ArchiveConfigurationError(
            "P.3 supports framework-dependent Desktop archives only"
        )


def _read_python_project_version(pyproject_path: Path) -> str:
    if not pyproject_path.is_file():
        raise ArchiveConfigurationError(f"pyproject.toml missing: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ArchiveConfigurationError("pyproject.toml project.version is required")
    return version


def _read_desktop_project_version(project_path: Path) -> str | None:
    if not project_path.is_file():
        return None
    root = ElementTree.parse(project_path).getroot()
    for property_group in root.findall("PropertyGroup"):
        version = property_group.findtext("Version")
        if version:
            return version
    return None


def _build_generated_files(
    *,
    repo_root: Path,
    input_dir: Path,
    runtime_audit: RuntimeAuditResult,
) -> dict[str, bytes]:
    flowweaver_license_path = repo_root / "LICENSE"
    python_license_path = input_dir / "EngineHost" / "python312" / "LICENSE.txt"
    if not flowweaver_license_path.is_file():
        raise ArchiveConfigurationError("repository LICENSE file is required")
    if not python_license_path.is_file():
        raise ArchiveConfigurationError("Python LICENSE.txt is required")

    third_party = {
        "status": "summary-only",
        "packages": [
            {"name": package.name, "version": package.version, "path": package.path}
            for package in runtime_audit.packages
        ],
    }
    return {
        FLOWWEAVER_LICENSE_ARCHIVE_PATH: flowweaver_license_path.read_bytes(),
        PYTHON_LICENSE_ARCHIVE_PATH: python_license_path.read_bytes(),
        THIRD_PARTY_LICENSES_ARCHIVE_PATH: _json_bytes(third_party),
    }


def _collect_input_file_entries(
    *,
    input_dir: Path,
    excluded_paths: set[str],
) -> list[ArchiveEntry]:
    entries: list[ArchiveEntry] = []
    for source_path in _iter_input_files(input_dir, excluded_paths=excluded_paths):
        archive_path = _archive_path_for_input_file(input_dir, source_path)
        entries.append(
            ArchiveEntry(
                path=archive_path,
                size=source_path.stat().st_size,
                sha256=_sha256_file(source_path),
            )
        )
    return entries


def _write_input_files(
    *,
    archive: zipfile.ZipFile,
    input_dir: Path,
    excluded_paths: set[str],
) -> None:
    for source_path in _iter_input_files(input_dir, excluded_paths=excluded_paths):
        archive.write(source_path, _archive_path_for_input_file(input_dir, source_path))


def _iter_input_files(input_dir: Path, *, excluded_paths: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(input_dir.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = _relative_posix(path, input_dir)
        if _is_excluded(relative, excluded_paths):
            continue
        files.append(path)
    return files


def _is_excluded(relative_path: str, excluded_paths: set[str]) -> bool:
    for excluded_path in excluded_paths:
        if excluded_path.endswith("/"):
            if relative_path.startswith(excluded_path):
                return True
        elif relative_path == excluded_path:
            return True
    return False


def _archive_path_for_input_file(input_dir: Path, source_path: Path) -> str:
    return f"{ARCHIVE_ROOT_NAME}/{_relative_posix(source_path, input_dir)}"


def _build_manifest(
    *,
    archive_name: str,
    target_runtime: str,
    release_version: str,
    python_project_version: str,
    desktop_project_version: str | None,
    runtime_audit: RuntimeAuditResult,
    entries: Sequence[ArchiveEntry],
    repo_root: Path,
) -> dict[str, object]:
    return {
        "manifest_schema_version": 1,
        "package_kind": "portable",
        "release_version": release_version,
        "archive_name": archive_name,
        "target_runtime": target_runtime,
        "created_at_utc": _utc_timestamp(),
        "git_commit": _git_output(repo_root, "rev-parse", "HEAD"),
        "git_dirty": _git_dirty(repo_root),
        "python_project_version": python_project_version,
        "desktop_project_version": desktop_project_version,
        "desktop_publish_mode": SUPPORTED_DESKTOP_PUBLISH_MODE,
        "desktop_self_contained": False,
        "dotnet_runtime_required": True,
        "dotnet_target_framework": "net10.0",
        "desktop_runtime_identifier": target_runtime,
        "python_version": runtime_audit.python_version,
        "pip_version": runtime_audit.pip_version,
        "runtime_audit_status": runtime_audit.status,
        "runtime_audit": runtime_audit.to_dict(),
        "manifest_path": MANIFEST_ARCHIVE_PATH,
        "manifest_integrity": "covered_by_external_zip_sha256",
        "entries": [entry.to_dict() for entry in entries],
        "excluded_paths": [
            f"{ARCHIVE_ROOT_NAME}/{path}" for path in runtime_audit.excluded_paths
        ],
        "licenses": [
            {
                "name": "FlowWeaver",
                "path": FLOWWEAVER_LICENSE_ARCHIVE_PATH,
                "kind": "project",
            },
            {
                "name": "Python",
                "path": PYTHON_LICENSE_ARCHIVE_PATH,
                "kind": "runtime",
            },
            {
                "name": "Third-party packages",
                "path": THIRD_PARTY_LICENSES_ARCHIVE_PATH,
                "kind": "summary",
            },
        ],
    }


def _git_output(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    output = completed.stdout.strip()
    return output or None


def _git_dirty(repo_root: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return bool(completed.stdout.strip())


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(data: object) -> bytes:
    return (
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _relative_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())

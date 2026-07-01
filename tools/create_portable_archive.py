from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    release_strict: bool = False,
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

    file_entries = _collect_input_file_entries(
        input_dir=input_dir,
        excluded_paths=set(runtime_audit.excluded_paths),
    )
    generated_files, third_party_metadata = _build_generated_files(
        repo_root=repo_root,
        input_dir=input_dir,
        runtime_audit=runtime_audit,
    )
    if release_strict:
        _validate_release_strict(
            repo_root=repo_root,
            input_dir=input_dir,
            runtime_audit=runtime_audit,
            third_party_metadata=third_party_metadata,
        )
    output_dir.mkdir(parents=True, exist_ok=True)
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
        release_strict=release_strict,
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
    parser.add_argument(
        "--release-strict",
        action="store_true",
        help=(
            "Enable formal release gates: reject warnings, dirty git state, "
            "missing git commit, and missing Desktop executable."
        ),
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
            release_strict=args.release_strict,
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
                "release_strict": args.release_strict,
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
) -> tuple[dict[str, bytes], dict[str, object]]:
    flowweaver_license_path = repo_root / "LICENSE"
    python_license_path = input_dir / "EngineHost" / "python312" / "LICENSE.txt"
    if not flowweaver_license_path.is_file():
        raise ArchiveConfigurationError("repository LICENSE file is required")
    if not python_license_path.is_file():
        raise ArchiveConfigurationError("Python LICENSE.txt is required")

    third_party_metadata, third_party_license_files = (
        _build_third_party_license_metadata(
            runtime_audit,
            repo_root=repo_root,
            input_dir=input_dir,
        )
    )
    return {
        FLOWWEAVER_LICENSE_ARCHIVE_PATH: flowweaver_license_path.read_bytes(),
        PYTHON_LICENSE_ARCHIVE_PATH: python_license_path.read_bytes(),
        THIRD_PARTY_LICENSES_ARCHIVE_PATH: _json_bytes(third_party_metadata),
        **third_party_license_files,
    }, third_party_metadata


def _validate_release_strict(
    *,
    repo_root: Path,
    input_dir: Path,
    runtime_audit: RuntimeAuditResult,
    third_party_metadata: dict[str, object],
) -> None:
    errors: list[str] = []
    if runtime_audit.status == "warning":
        errors.append("runtime_audit_warning")
    elif runtime_audit.status != "checked":
        errors.append(f"runtime_audit_{runtime_audit.status}")
    if third_party_metadata.get("warnings"):
        errors.append("third_party_license_warning")
    if _git_output(repo_root, "rev-parse", "HEAD") is None:
        errors.append("git_commit_unavailable")
    if _git_dirty(repo_root):
        errors.append("git_worktree_dirty")
    if not (input_dir / "Desktop" / "Avalonia_UI.exe").is_file():
        errors.append("desktop_executable_missing")
    if errors:
        joined_errors = ", ".join(sorted(set(errors)))
        raise ArchiveConfigurationError(
            f"release strict rejected portable input: {joined_errors}"
        )


def _build_third_party_license_metadata(
    runtime_audit: RuntimeAuditResult,
    *,
    repo_root: Path,
    input_dir: Path,
) -> tuple[dict[str, object], dict[str, bytes]]:
    copied_python_license_files = _collect_python_license_file_copies(
        runtime_audit=runtime_audit,
        input_dir=input_dir,
    )
    packages = [
        _python_package_license_dict(
            package,
            copied_license_files=copied_python_license_files.copied_paths_by_package[
                package.path
            ],
            copy_warnings=copied_python_license_files.warnings_by_package[
                package.path
            ],
        )
        for package in runtime_audit.packages
    ]
    (
        dotnet_packages,
        dotnet_sources,
        dotnet_warnings,
        dotnet_license_files,
    ) = _collect_dotnet_packages(repo_root=repo_root, input_dir=input_dir)
    packages.extend(dotnet_packages)
    packages.sort(key=lambda package: (str(package["ecosystem"]), str(package["name"])))

    warnings = sorted(
        {
            warning
            for package in packages
            for warning in package["warnings"]
        }
        | set(dotnet_warnings)
    )
    generated_from: dict[str, object] = {
        "python_runtime": "EngineHost/python312",
    }
    if dotnet_sources:
        generated_from["dotnet_sources"] = dotnet_sources
    return {
        "schema_version": 1,
        "status": "metadata-and-files",
        "generated_from": generated_from,
        "packages": packages,
        "warnings": warnings,
    }, {
        **copied_python_license_files.generated_files,
        **dotnet_license_files,
    }


@dataclass(frozen=True)
class CopiedLicenseFiles:
    generated_files: dict[str, bytes]
    copied_paths_by_package: dict[str, list[str]]
    warnings_by_package: dict[str, list[str]]


@dataclass(frozen=True)
class NuGetLicenseMetadata:
    metadata_source_suffix: str | None
    license_expression: str | None
    license_text: str | None
    license_files: tuple[str, ...]
    copied_license_files: tuple[str, ...]
    generated_files: dict[str, bytes]
    license_status: str
    warnings: tuple[str, ...]


def _python_package_license_dict(
    package: object,
    *,
    copied_license_files: Sequence[str],
    copy_warnings: Sequence[str],
) -> dict[str, object]:
    warnings = sorted(set(package.warnings) | set(copy_warnings))
    return {
        "ecosystem": package.ecosystem,
        "name": package.name,
        "version": package.version,
        "path": package.path,
        "metadata_source": package.metadata_source,
        "license_expression": package.license_expression,
        "license_text": package.license_text,
        "license_classifiers": list(package.license_classifiers),
        "license_files": list(package.license_files),
        "copied_license_files": list(copied_license_files),
        "license_status": package.license_status,
        "warnings": warnings,
    }


def _collect_python_license_file_copies(
    *,
    runtime_audit: RuntimeAuditResult,
    input_dir: Path,
) -> CopiedLicenseFiles:
    generated_files: dict[str, bytes] = {}
    copied_paths_by_package: dict[str, list[str]] = {
        package.path: [] for package in runtime_audit.packages
    }
    warnings_by_package: dict[str, list[str]] = {
        package.path: [] for package in runtime_audit.packages
    }

    for package in runtime_audit.packages:
        for license_file in package.license_files:
            source_path = _resolve_input_relative_file(
                input_dir=input_dir,
                relative_path=license_file,
            )
            if source_path is None:
                warnings_by_package[package.path].append(
                    "license_file_source_outside_input"
                )
                continue
            if not source_path.is_file():
                warnings_by_package[package.path].append("license_file_source_missing")
                continue

            archive_path = _third_party_python_license_archive_path(
                package_name=package.name,
                package_path=package.path,
                license_file=license_file,
            )
            content = source_path.read_bytes()
            existing_content = generated_files.get(archive_path)
            if existing_content is not None and existing_content != content:
                warnings_by_package[package.path].append(
                    "license_file_copy_name_conflict"
                )
                continue
            generated_files[archive_path] = content
            copied_paths_by_package[package.path].append(archive_path)

    for paths in copied_paths_by_package.values():
        paths.sort()
    for warnings in warnings_by_package.values():
        warnings[:] = sorted(set(warnings))
    return CopiedLicenseFiles(
        generated_files=generated_files,
        copied_paths_by_package=copied_paths_by_package,
        warnings_by_package=warnings_by_package,
    )


def _resolve_input_relative_file(
    *,
    input_dir: Path,
    relative_path: str,
) -> Path | None:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        return None
    source_path = (input_dir / path).resolve()
    try:
        source_path.relative_to(input_dir.resolve())
    except ValueError:
        return None
    return source_path


def _third_party_python_license_archive_path(
    *,
    package_name: str,
    package_path: str,
    license_file: str,
) -> str:
    prefix = f"{package_path}/"
    if license_file.startswith(prefix):
        suffix = license_file[len(prefix) :]
    else:
        suffix = Path(license_file).name
    suffix_path = Path(suffix)
    if suffix_path.is_absolute() or ".." in suffix_path.parts:
        suffix = Path(license_file).name
    return (
        f"{LICENSE_DIR_ARCHIVE_PATH}/third-party/python/"
        f"{package_name}/{Path(suffix).as_posix()}"
    )


def _collect_dotnet_packages(
    *,
    repo_root: Path,
    input_dir: Path,
) -> tuple[list[dict[str, object]], list[str], list[str], dict[str, bytes]]:
    if not _desktop_payload_present(input_dir):
        return [], [], [], {}

    assets_path = repo_root / "Avalonia_UI" / "obj" / "project.assets.json"
    if assets_path.is_file():
        source = _relative_posix(assets_path, repo_root)
        packages, license_files = _parse_dotnet_package_libraries(
            data=_read_json_file(assets_path),
            source_path=source,
            metadata_source="project.assets.json",
        )
        return packages, [source], [], license_files

    deps_path = input_dir / "Desktop" / "Avalonia_UI.deps.json"
    if deps_path.is_file():
        source = _relative_posix(deps_path, input_dir)
        packages, license_files = _parse_dotnet_package_libraries(
            data=_read_json_file(deps_path),
            source_path=source,
            metadata_source="deps.json",
        )
        return packages, [source], [], license_files

    return [], [], ["dotnet_dependency_source_missing"], {}


def _desktop_payload_present(input_dir: Path) -> bool:
    desktop_dir = input_dir / "Desktop"
    return desktop_dir.is_dir() and any(
        path.is_file() for path in desktop_dir.rglob("*")
    )


def _parse_dotnet_package_libraries(
    *,
    data: object,
    source_path: str,
    metadata_source: str,
) -> tuple[list[dict[str, object]], dict[str, bytes]]:
    if not isinstance(data, dict):
        return [], {}
    libraries = data.get("libraries")
    if not isinstance(libraries, dict):
        return [], {}

    packages: list[dict[str, object]] = []
    generated_files: dict[str, bytes] = {}
    for key, value in sorted(libraries.items(), key=lambda item: item[0].lower()):
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        if value.get("type") != "package":
            continue
        parsed = _parse_dotnet_package_key(key)
        if parsed is None:
            continue
        name, version = parsed
        package, package_license_files = _build_dotnet_package_license_dict(
            name=name,
            version=version,
            source_path=source_path,
            metadata_source=metadata_source,
        )
        packages.append(package)
        generated_files.update(package_license_files)
    return packages, generated_files


def _build_dotnet_package_license_dict(
    *,
    name: str,
    version: str,
    source_path: str,
    metadata_source: str,
) -> tuple[dict[str, object], dict[str, bytes]]:
    license_metadata = _read_nuget_license_metadata(name=name, version=version)
    effective_metadata_source = metadata_source
    if license_metadata.metadata_source_suffix is not None:
        effective_metadata_source = (
            f"{metadata_source}+{license_metadata.metadata_source_suffix}"
        )

    return {
        "ecosystem": "dotnet",
        "name": name,
        "version": version,
        "path": f"{source_path}#{name}/{version}",
        "metadata_source": effective_metadata_source,
        "license_expression": license_metadata.license_expression,
        "license_text": license_metadata.license_text,
        "license_classifiers": [],
        "license_files": list(license_metadata.license_files),
        "copied_license_files": list(license_metadata.copied_license_files),
        "license_status": license_metadata.license_status,
        "warnings": list(license_metadata.warnings),
    }, license_metadata.generated_files


def _parse_dotnet_package_key(key: str) -> tuple[str, str] | None:
    if "/" not in key:
        return None
    name, version = key.rsplit("/", 1)
    if not name or not version:
        return None
    return name, version


def _read_nuget_license_metadata(*, name: str, version: str) -> NuGetLicenseMetadata:
    for root in _nuget_cache_roots():
        package_dir = root / name.lower() / version.lower()
        nuspec_path = package_dir / f"{name.lower()}.nuspec"
        if not nuspec_path.is_file():
            continue
        root_element = ElementTree.parse(nuspec_path).getroot()
        for element in root_element.iter():
            if _xml_local_name(element.tag) != "license":
                continue
            license_type = element.attrib.get("type")
            if license_type == "expression" and element.text:
                expression = element.text.strip()
                if expression:
                    return NuGetLicenseMetadata(
                        metadata_source_suffix="nuspec",
                        license_expression=expression,
                        license_text=None,
                        license_files=(),
                        copied_license_files=(),
                        generated_files={},
                        license_status="metadata_found",
                        warnings=(),
                    )
            if license_type == "file" and element.text:
                return _read_nuget_license_file_metadata(
                    name=name,
                    version=version,
                    package_dir=package_dir,
                    declared_file=element.text.strip(),
                )
    return NuGetLicenseMetadata(
        metadata_source_suffix=None,
        license_expression=None,
        license_text=None,
        license_files=(),
        copied_license_files=(),
        generated_files={},
        license_status="missing_license_metadata",
        warnings=("nuget_license_metadata_unavailable",),
    )


def _read_nuget_license_file_metadata(
    *,
    name: str,
    version: str,
    package_dir: Path,
    declared_file: str,
) -> NuGetLicenseMetadata:
    license_file = Path(declared_file)
    source_label = (
        f"nuget-cache/{name.lower()}/{version.lower()}/"
        f"{license_file.as_posix()}"
    )
    if (
        not declared_file
        or license_file.is_absolute()
        or ".." in license_file.parts
    ):
        return NuGetLicenseMetadata(
            metadata_source_suffix="nuspec",
            license_expression=None,
            license_text=None,
            license_files=(source_label,),
            copied_license_files=(),
            generated_files={},
            license_status="license_file_missing",
            warnings=("nuget_license_file_invalid",),
        )

    source_path = package_dir / license_file
    if not source_path.is_file():
        return NuGetLicenseMetadata(
            metadata_source_suffix="nuspec",
            license_expression=None,
            license_text=None,
            license_files=(source_label,),
            copied_license_files=(),
            generated_files={},
            license_status="license_file_missing",
            warnings=("nuget_license_file_missing",),
        )

    archive_path = _third_party_dotnet_license_archive_path(
        package_name=name,
        version=version,
        license_file=license_file,
    )
    return NuGetLicenseMetadata(
        metadata_source_suffix="nuspec",
        license_expression=None,
        license_text=None,
        license_files=(source_label,),
        copied_license_files=(archive_path,),
        generated_files={archive_path: source_path.read_bytes()},
        license_status="license_file_found",
        warnings=(),
    )


def _third_party_dotnet_license_archive_path(
    *,
    package_name: str,
    version: str,
    license_file: Path,
) -> str:
    suffix = license_file.as_posix()
    suffix_path = Path(suffix)
    if suffix_path.is_absolute() or ".." in suffix_path.parts:
        suffix = license_file.name
    return (
        f"{LICENSE_DIR_ARCHIVE_PATH}/third-party/dotnet/"
        f"{package_name}/{version}/{suffix}"
    )


def _nuget_cache_roots() -> tuple[Path, ...]:
    configured = os.environ.get("NUGET_PACKAGES")
    if configured:
        return (Path(configured),)
    return (Path.home() / ".nuget" / "packages",)


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _read_json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


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
    release_strict: bool,
) -> dict[str, object]:
    return {
        "manifest_schema_version": 1,
        "package_kind": "portable",
        "release_version": release_version,
        "archive_name": archive_name,
        "target_runtime": target_runtime,
        "release_strict": release_strict,
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
                "kind": "metadata",
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

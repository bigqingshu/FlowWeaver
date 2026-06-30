from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

_ARCHIVE = None


def archive_module() -> ModuleType:
    global _ARCHIVE
    if _ARCHIVE is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "tools" / "create_portable_archive.py"
        spec = importlib.util.spec_from_file_location(
            "flowweaver_create_portable_archive",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _ARCHIVE = module
    return _ARCHIVE


def test_create_portable_archive_generates_zip_manifest_hash_and_licenses(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )

    result = archive_module().create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        command_runner=_fake_command_runner,
    )

    assert result.archive_path.name == "FlowWeaverPortable-0.1.0-win-x64.zip"
    assert result.sha256_path.name == "FlowWeaverPortable-0.1.0-win-x64.zip.sha256"
    assert result.archive_path.is_file()
    assert result.sha256_path.is_file()
    assert result.sha256_path.read_text(encoding="utf-8") == (
        f"{_sha256_file(result.archive_path)}  {result.archive_path.name}\n"
    )

    with zipfile.ZipFile(result.archive_path) as archive:
        names = set(archive.namelist())
        assert "FlowWeaverPortable/start_flowweaver.cmd" in names
        assert "FlowWeaverPortable/EngineHost/python312/python.exe" in names
        assert "FlowWeaverPortable/release-manifest.json" in names
        assert "FlowWeaverPortable/licenses/FlowWeaver-LICENSE.txt" in names
        assert "FlowWeaverPortable/licenses/Python-LICENSE.txt" in names
        assert "FlowWeaverPortable/licenses/third-party-licenses.json" in names

        manifest = json.loads(
            archive.read("FlowWeaverPortable/release-manifest.json").decode("utf-8")
        )
        assert manifest["release_version"] == "0.1.0"
        assert manifest["python_project_version"] == "0.1.0"
        assert manifest["desktop_project_version"] == "0.1.0-desktop"
        assert manifest["target_runtime"] == "win-x64"
        assert manifest["desktop_publish_mode"] == "framework-dependent"
        assert manifest["desktop_self_contained"] is False
        assert manifest["dotnet_runtime_required"] is True
        assert manifest["runtime_audit_status"] == "checked"
        assert manifest["manifest_path"] == "FlowWeaverPortable/release-manifest.json"
        assert manifest["manifest_integrity"] == "covered_by_external_zip_sha256"

        entries = {entry["path"]: entry for entry in manifest["entries"]}
        assert "FlowWeaverPortable/release-manifest.json" not in entries
        assert set(entries) == names - {"FlowWeaverPortable/release-manifest.json"}
        for name, entry in entries.items():
            content = archive.read(name)
            assert entry["size"] == len(content)
            assert entry["sha256"] == hashlib.sha256(content).hexdigest()

        third_party = json.loads(
            archive.read(
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ).decode("utf-8")
        )
        assert third_party["status"] == "summary-only"
        assert third_party["packages"] == [
            {
                "name": "fastapi",
                "version": "0.124.0",
                "path": (
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info"
                ),
            }
        ]


def test_create_portable_archive_accepts_warning_audit_and_excludes_cache(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"pytest": "8.4.0"},
    )
    cache_dir = (
        portable_root
        / "EngineHost"
        / "python312"
        / "Lib"
        / "site-packages"
        / "__pycache__"
    )
    cache_dir.mkdir()
    (cache_dir / "module.cpython-312.pyc").write_text("", encoding="utf-8")

    result = archive_module().create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        command_runner=_fake_command_runner,
    )

    with zipfile.ZipFile(result.archive_path) as archive:
        names = set(archive.namelist())
        assert not any("__pycache__" in name for name in names)
        assert not any(name.endswith(".pyc") for name in names)
        manifest = json.loads(
            archive.read("FlowWeaverPortable/release-manifest.json").decode("utf-8")
        )
        assert manifest["runtime_audit_status"] == "warning"
        assert (
            "FlowWeaverPortable/EngineHost/python312/Lib/site-packages/__pycache__/"
            in manifest["excluded_paths"]
        )
        assert (
            "FlowWeaverPortable/EngineHost/python312/Lib/site-packages/__pycache__/"
            "module.cpython-312.pyc"
            in manifest["excluded_paths"]
        )


def test_create_portable_archive_rejects_version_mismatch(tmp_path: Path) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="must match pyproject",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            version="9.9.9",
            command_runner=_fake_command_runner,
        )


def test_create_portable_archive_rejects_output_outside_tmp(tmp_path: Path) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="output_dir must be inside",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=tmp_path / "outside-dist",
            command_runner=_fake_command_runner,
        )


def test_create_portable_archive_rejects_self_contained_mode(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="framework-dependent",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            desktop_publish_mode="self-contained",
            command_runner=_fake_command_runner,
        )


def test_create_portable_archive_rejects_runtime_audit_errors(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    runtime_dir = portable_root / "EngineHost" / "runtime"
    (runtime_dir / "config").mkdir(parents=True)
    (runtime_dir / "config" / "local_api_token").write_text(
        "secret",
        encoding="utf-8",
    )

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="runtime audit rejected",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            command_runner=_fake_command_runner,
        )

    assert not (repo_root / ".tmp" / "dist").exists()


def test_create_portable_archive_rejects_existing_archive(tmp_path: Path) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    output_dir = repo_root / ".tmp" / "dist"
    output_dir.mkdir(parents=True)
    (output_dir / "FlowWeaverPortable-0.1.0-win-x64.zip").write_text(
        "old",
        encoding="utf-8",
    )

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="already exists",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=output_dir,
            command_runner=_fake_command_runner,
        )


def _create_repo_with_portable_layout(
    tmp_path: Path,
    *,
    packages: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    portable_root = repo_root / ".tmp" / "FlowWeaverPortable"
    python_dir = portable_root / "EngineHost" / "python312"
    site_packages = python_dir / "Lib" / "site-packages"
    desktop_dir = repo_root / "Avalonia_UI"
    site_packages.mkdir(parents=True)
    desktop_dir.mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "flowweaver"',
                'version = "0.1.0"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo_root / "LICENSE").write_text("MIT test license", encoding="utf-8")
    (desktop_dir / "Avalonia_UI.csproj").write_text(
        "\n".join(
            [
                '<Project Sdk="Microsoft.NET.Sdk">',
                "  <PropertyGroup>",
                "    <TargetFramework>net10.0</TargetFramework>",
                "    <Version>0.1.0-desktop</Version>",
                "  </PropertyGroup>",
                "</Project>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (portable_root / "start_flowweaver.cmd").write_text(
        "portable launcher",
        encoding="utf-8",
    )
    (portable_root / "start_flowweaver_desktop.cmd").write_text(
        "desktop launcher",
        encoding="utf-8",
    )
    (portable_root / "EngineHost" / "src" / "flowweaver").mkdir(parents=True)
    (portable_root / "EngineHost" / "src" / "flowweaver" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (python_dir / "python.exe").write_text("", encoding="utf-8")
    (python_dir / "python312._pth").write_text(
        "\n".join(["python312.zip", ".", "import site"]),
        encoding="utf-8",
    )
    (python_dir / "LICENSE.txt").write_text("Python license", encoding="utf-8")
    for name, version in (packages or {}).items():
        (site_packages / f"{name}-{version}.dist-info").mkdir()
    return repo_root, portable_root


def _fake_command_runner(
    command: tuple[str, ...],
) -> str:
    if command[1:] == ("--version",):
        return "Python 3.12.10"
    if command[1:] == ("-m", "pip", "--version"):
        return "pip 26.1.2 from fake (python 3.12)"
    raise AssertionError(f"unexpected command: {command}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

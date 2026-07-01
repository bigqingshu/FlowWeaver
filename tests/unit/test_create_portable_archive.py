from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType, SimpleNamespace

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
    dist_info_dir = (
        portable_root
        / "EngineHost"
        / "python312"
        / "Lib"
        / "site-packages"
        / "fastapi-0.124.0.dist-info"
    )
    (dist_info_dir / "METADATA").write_text(
        "\n".join(
            [
                "Metadata-Version: 2.4",
                "Name: fastapi",
                "Version: 0.124.0",
                "License-Expression: MIT",
                "Classifier: License :: OSI Approved :: MIT License",
                "License-File: LICENSE",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dist_info_dir / "LICENSE").write_text("MIT license", encoding="utf-8")

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
        assert "FlowWeaverPortable/docs/README.txt" in names
        assert "FlowWeaverPortable/docs/FlowWeaver_便携版用户手册.md" in names
        assert "FlowWeaverPortable/EngineHost/python312/python.exe" in names
        assert "FlowWeaverPortable/release-manifest.json" in names
        assert "FlowWeaverPortable/licenses/FlowWeaver-LICENSE.txt" in names
        assert "FlowWeaverPortable/licenses/Python-LICENSE.txt" in names
        assert "FlowWeaverPortable/licenses/third-party-licenses.json" in names
        assert (
            "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE" in names
        )

        manifest = json.loads(
            archive.read("FlowWeaverPortable/release-manifest.json").decode("utf-8")
        )
        assert manifest["release_version"] == "0.1.0"
        assert manifest["python_project_version"] == "0.1.0"
        assert manifest["desktop_project_version"] == "0.1.0-desktop"
        assert manifest["target_runtime"] == "win-x64"
        assert manifest["release_strict"] is False
        assert manifest["desktop_publish_mode"] == "framework-dependent"
        assert manifest["desktop_self_contained"] is False
        assert manifest["dotnet_runtime_required"] is True
        assert manifest["runtime_audit_status"] == "checked"
        assert manifest["manifest_path"] == "FlowWeaverPortable/release-manifest.json"
        assert manifest["manifest_integrity"] == "covered_by_external_zip_sha256"
        license_entries = {
            license_entry["path"]: license_entry
            for license_entry in manifest["licenses"]
        }
        assert (
            license_entries[
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ]["kind"]
            == "metadata"
        )

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
        assert third_party["schema_version"] == 1
        assert third_party["status"] == "metadata-and-files"
        assert third_party["generated_from"] == {
            "python_runtime": "EngineHost/python312"
        }
        assert third_party["warnings"] == []
        assert third_party["packages"] == [
            {
                "ecosystem": "python",
                "name": "fastapi",
                "version": "0.124.0",
                "path": (
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info"
                ),
                "metadata_source": "METADATA",
                "license_expression": "MIT",
                "license_text": None,
                "license_classifiers": [
                    "License :: OSI Approved :: MIT License"
                ],
                "license_files": [
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info/LICENSE"
                ],
                "copied_license_files": [
                    "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE"
                ],
                "license_status": "license_file_found",
                "warnings": [],
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
        third_party = json.loads(
            archive.read(
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ).decode("utf-8")
        )
        assert third_party["status"] == "metadata-and-files"
        assert third_party["warnings"] == ["metadata_file_missing"]
        assert third_party["packages"][0]["license_status"] == "missing_metadata"
        assert third_party["packages"][0]["copied_license_files"] == []
        assert third_party["packages"][0]["warnings"] == ["metadata_file_missing"]


def test_create_portable_archive_release_strict_rejects_runtime_audit_warning(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"pytest": "8.4.0"},
    )
    _write_python_package_license_metadata(
        portable_root,
        name="pytest",
        version="8.4.0",
    )
    _write_portable_desktop_executable(portable_root)

    with pytest.raises(
        archive_module().ArchiveConfigurationError,
        match="runtime_audit_warning",
    ):
        archive_module().create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            release_strict=True,
            command_runner=_fake_command_runner,
        )

    assert not (repo_root / ".tmp" / "dist").exists()


def test_create_portable_archive_release_strict_rejects_license_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = archive_module()
    monkeypatch.setattr(module, "_git_output", lambda *args: "abc123")
    monkeypatch.setattr(module, "_git_dirty", lambda repo_root: False)
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )
    _write_portable_desktop_executable(portable_root)

    with pytest.raises(
        module.ArchiveConfigurationError,
        match="third_party_license_warning",
    ):
        module.create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            release_strict=True,
            command_runner=_fake_command_runner,
        )

    assert not (repo_root / ".tmp" / "dist").exists()


def test_create_portable_archive_release_strict_rejects_dirty_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = archive_module()
    monkeypatch.setattr(module, "_git_output", lambda *args: "abc123")
    monkeypatch.setattr(module, "_git_dirty", lambda repo_root: True)
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )
    _write_python_package_license_metadata(portable_root)
    _write_portable_desktop_executable(portable_root)
    _write_empty_dotnet_project_assets(repo_root)

    with pytest.raises(
        module.ArchiveConfigurationError,
        match="git_worktree_dirty",
    ):
        module.create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            release_strict=True,
            command_runner=_fake_command_runner,
        )

    assert not (repo_root / ".tmp" / "dist").exists()


def test_create_portable_archive_release_strict_rejects_missing_desktop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = archive_module()
    monkeypatch.setattr(module, "_git_output", lambda *args: "abc123")
    monkeypatch.setattr(module, "_git_dirty", lambda repo_root: False)
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )
    _write_python_package_license_metadata(portable_root)

    with pytest.raises(
        module.ArchiveConfigurationError,
        match="desktop_executable_missing",
    ):
        module.create_portable_archive(
            repo_root=repo_root,
            input_dir=portable_root,
            output_dir=repo_root / ".tmp" / "dist",
            release_strict=True,
            command_runner=_fake_command_runner,
        )

    assert not (repo_root / ".tmp" / "dist").exists()


def test_create_portable_archive_release_strict_accepts_clean_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = archive_module()
    monkeypatch.setattr(module, "_git_output", lambda *args: "abc123")
    monkeypatch.setattr(module, "_git_dirty", lambda repo_root: False)
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )
    _write_python_package_license_metadata(portable_root)
    _write_portable_desktop_executable(portable_root)
    _write_empty_dotnet_project_assets(repo_root)

    result = module.create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        release_strict=True,
        command_runner=_fake_command_runner,
    )

    assert result.archive_path.is_file()
    assert result.manifest["release_strict"] is True


def test_create_portable_archive_parse_args_accepts_release_strict() -> None:
    args = archive_module().parse_args(["--release-strict"])

    assert args.release_strict is True


def test_create_portable_archive_collects_dotnet_metadata_from_project_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    (portable_root / "Desktop").mkdir()
    (portable_root / "Desktop" / "Avalonia_UI.exe").write_text("", encoding="utf-8")
    assets_path = repo_root / "Avalonia_UI" / "obj" / "project.assets.json"
    assets_path.parent.mkdir(parents=True)
    assets_path.write_text(
        json.dumps(
            {
                "version": 3,
                "libraries": {
                    "Example.Package/1.2.3": {"type": "package"},
                    "Avalonia_UI/0.1.0": {"type": "project"},
                },
            }
        ),
        encoding="utf-8",
    )
    nuget_root = tmp_path / "nuget"
    package_dir = nuget_root / "example.package" / "1.2.3"
    package_dir.mkdir(parents=True)
    (package_dir / "example.package.nuspec").write_text(
        "\n".join(
            [
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                '    <license type="expression">MIT</license>',
                "  </metadata>",
                "</package>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NUGET_PACKAGES", str(nuget_root))

    result = archive_module().create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        command_runner=_fake_command_runner,
    )

    with zipfile.ZipFile(result.archive_path) as archive:
        third_party = json.loads(
            archive.read(
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ).decode("utf-8")
        )

    assert third_party["generated_from"]["dotnet_sources"] == [
        "Avalonia_UI/obj/project.assets.json"
    ]
    assert third_party["warnings"] == []
    assert third_party["packages"] == [
        {
            "ecosystem": "dotnet",
            "name": "Example.Package",
            "version": "1.2.3",
            "path": (
                "Avalonia_UI/obj/project.assets.json#"
                "Example.Package/1.2.3"
            ),
            "metadata_source": "project.assets.json+nuspec",
            "license_expression": "MIT",
            "license_text": None,
            "license_classifiers": [],
            "license_files": [],
            "copied_license_files": [],
            "license_status": "metadata_found",
            "warnings": [],
        }
    ]


def test_create_portable_archive_copies_dotnet_nuget_license_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    (portable_root / "Desktop").mkdir()
    (portable_root / "Desktop" / "Avalonia_UI.exe").write_text("", encoding="utf-8")
    assets_path = repo_root / "Avalonia_UI" / "obj" / "project.assets.json"
    assets_path.parent.mkdir(parents=True)
    assets_path.write_text(
        json.dumps(
            {
                "version": 3,
                "libraries": {
                    "File.Package/1.2.3": {"type": "package"},
                },
            }
        ),
        encoding="utf-8",
    )
    nuget_root = tmp_path / "nuget"
    package_dir = nuget_root / "file.package" / "1.2.3"
    package_dir.mkdir(parents=True)
    (package_dir / "file.package.nuspec").write_text(
        "\n".join(
            [
                '<package xmlns="http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd">',
                "  <metadata>",
                '    <license type="file">LICENSE</license>',
                "  </metadata>",
                "</package>",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_dir / "LICENSE").write_text("NuGet package license", encoding="utf-8")
    monkeypatch.setenv("NUGET_PACKAGES", str(nuget_root))

    result = archive_module().create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        command_runner=_fake_command_runner,
    )

    copied_path = (
        "FlowWeaverPortable/licenses/third-party/dotnet/"
        "File.Package/1.2.3/LICENSE"
    )
    with zipfile.ZipFile(result.archive_path) as archive:
        assert archive.read(copied_path).decode("utf-8") == "NuGet package license"
        third_party = json.loads(
            archive.read(
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ).decode("utf-8")
        )

    assert third_party["warnings"] == []
    assert third_party["packages"] == [
        {
            "ecosystem": "dotnet",
            "name": "File.Package",
            "version": "1.2.3",
            "path": (
                "Avalonia_UI/obj/project.assets.json#"
                "File.Package/1.2.3"
            ),
            "metadata_source": "project.assets.json+nuspec",
            "license_expression": None,
            "license_text": None,
            "license_classifiers": [],
            "license_files": ["nuget-cache/file.package/1.2.3/LICENSE"],
            "copied_license_files": [copied_path],
            "license_status": "license_file_found",
            "warnings": [],
        }
    ]


def test_create_portable_archive_collects_dotnet_metadata_from_deps_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    desktop_dir = portable_root / "Desktop"
    desktop_dir.mkdir()
    (desktop_dir / "Avalonia_UI.deps.json").write_text(
        json.dumps(
            {
                "libraries": {
                    "Example.Package/1.2.3": {"type": "package"},
                    "Avalonia_UI/0.1.0": {"type": "project"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("NUGET_PACKAGES", str(tmp_path / "empty-nuget"))

    result = archive_module().create_portable_archive(
        repo_root=repo_root,
        input_dir=portable_root,
        output_dir=repo_root / ".tmp" / "dist",
        command_runner=_fake_command_runner,
    )

    with zipfile.ZipFile(result.archive_path) as archive:
        third_party = json.loads(
            archive.read(
                "FlowWeaverPortable/licenses/third-party-licenses.json"
            ).decode("utf-8")
        )

    assert third_party["generated_from"]["dotnet_sources"] == [
        "Desktop/Avalonia_UI.deps.json"
    ]
    assert third_party["warnings"] == ["nuget_license_metadata_unavailable"]
    assert third_party["packages"] == [
        {
            "ecosystem": "dotnet",
            "name": "Example.Package",
            "version": "1.2.3",
            "path": "Desktop/Avalonia_UI.deps.json#Example.Package/1.2.3",
            "metadata_source": "deps.json",
            "license_expression": None,
            "license_text": None,
            "license_classifiers": [],
            "license_files": [],
            "copied_license_files": [],
            "license_status": "missing_license_metadata",
            "warnings": ["nuget_license_metadata_unavailable"],
        }
    ]


def test_third_party_license_metadata_records_missing_python_license_source(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    runtime_audit = SimpleNamespace(
        packages=(
            SimpleNamespace(
                ecosystem="python",
                name="fastapi",
                version="0.124.0",
                path=(
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info"
                ),
                metadata_source="METADATA",
                license_expression="MIT",
                license_text=None,
                license_classifiers=(),
                license_files=(
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info/MISSING-LICENSE",
                ),
                license_status="license_file_found",
                warnings=(),
            ),
        )
    )

    metadata, generated_files = archive_module()._build_third_party_license_metadata(
        runtime_audit,
        repo_root=repo_root,
        input_dir=portable_root,
    )

    assert generated_files == {}
    assert metadata["warnings"] == ["license_file_source_missing"]
    assert metadata["packages"][0]["copied_license_files"] == []
    assert metadata["packages"][0]["warnings"] == ["license_file_source_missing"]


def test_third_party_license_metadata_records_outside_python_license_source(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(tmp_path)
    runtime_audit = SimpleNamespace(
        packages=(
            SimpleNamespace(
                ecosystem="python",
                name="fastapi",
                version="0.124.0",
                path=(
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info"
                ),
                metadata_source="METADATA",
                license_expression="MIT",
                license_text=None,
                license_classifiers=(),
                license_files=("../outside/LICENSE",),
                license_status="license_file_found",
                warnings=(),
            ),
        )
    )

    metadata, generated_files = archive_module()._build_third_party_license_metadata(
        runtime_audit,
        repo_root=repo_root,
        input_dir=portable_root,
    )

    assert generated_files == {}
    assert metadata["warnings"] == ["license_file_source_outside_input"]
    assert metadata["packages"][0]["copied_license_files"] == []
    assert metadata["packages"][0]["warnings"] == [
        "license_file_source_outside_input"
    ]


def test_third_party_license_metadata_records_python_license_copy_conflict(
    tmp_path: Path,
) -> None:
    repo_root, portable_root = _create_repo_with_portable_layout(
        tmp_path,
        packages={"fastapi": "0.124.0"},
    )
    dist_info_dir = (
        portable_root
        / "EngineHost"
        / "python312"
        / "Lib"
        / "site-packages"
        / "fastapi-0.124.0.dist-info"
    )
    (dist_info_dir / "LICENSE").write_text("one", encoding="utf-8")
    other_dist_info_dir = (
        portable_root
        / "EngineHost"
        / "python312"
        / "Lib"
        / "site-packages"
        / "other-1.0.0.dist-info"
    )
    other_dist_info_dir.mkdir()
    (other_dist_info_dir / "LICENSE").write_text("two", encoding="utf-8")
    runtime_audit = SimpleNamespace(
        packages=(
            SimpleNamespace(
                ecosystem="python",
                name="fastapi",
                version="0.124.0",
                path=(
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info"
                ),
                metadata_source="METADATA",
                license_expression="MIT",
                license_text=None,
                license_classifiers=(),
                license_files=(
                    "EngineHost/python312/Lib/site-packages/"
                    "fastapi-0.124.0.dist-info/LICENSE",
                    "EngineHost/python312/Lib/site-packages/"
                    "other-1.0.0.dist-info/LICENSE",
                ),
                license_status="license_file_found",
                warnings=(),
            ),
        )
    )

    metadata, generated_files = archive_module()._build_third_party_license_metadata(
        runtime_audit,
        repo_root=repo_root,
        input_dir=portable_root,
    )

    assert list(generated_files) == [
        "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE"
    ]
    assert metadata["warnings"] == ["license_file_copy_name_conflict"]
    assert metadata["packages"][0]["copied_license_files"] == [
        "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE"
    ]
    assert metadata["packages"][0]["warnings"] == [
        "license_file_copy_name_conflict"
    ]


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
    (portable_root / "docs").mkdir()
    (portable_root / "docs" / "README.txt").write_text(
        "See docs/FlowWeaver_便携版用户手册.md",
        encoding="utf-8",
    )
    (portable_root / "docs" / "FlowWeaver_便携版用户手册.md").write_text(
        "# FlowWeaver 便携版用户手册\n",
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


def _write_python_package_license_metadata(
    portable_root: Path,
    *,
    name: str = "fastapi",
    version: str = "0.124.0",
) -> None:
    dist_info_dir = (
        portable_root
        / "EngineHost"
        / "python312"
        / "Lib"
        / "site-packages"
        / f"{name}-{version}.dist-info"
    )
    (dist_info_dir / "METADATA").write_text(
        "\n".join(
            [
                "Metadata-Version: 2.4",
                f"Name: {name}",
                f"Version: {version}",
                "License-Expression: MIT",
                "License-File: LICENSE",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dist_info_dir / "LICENSE").write_text("MIT license", encoding="utf-8")


def _write_portable_desktop_executable(portable_root: Path) -> None:
    desktop_dir = portable_root / "Desktop"
    desktop_dir.mkdir(exist_ok=True)
    (desktop_dir / "Avalonia_UI.exe").write_text("", encoding="utf-8")


def _write_empty_dotnet_project_assets(repo_root: Path) -> None:
    assets_path = repo_root / "Avalonia_UI" / "obj" / "project.assets.json"
    assets_path.parent.mkdir(parents=True)
    assets_path.write_text(
        json.dumps({"version": 3, "libraries": {}}),
        encoding="utf-8",
    )


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

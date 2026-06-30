from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

_AUDIT = None


def audit_module() -> ModuleType:
    global _AUDIT
    if _AUDIT is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "tools" / "portable_runtime_audit.py"
        spec = importlib.util.spec_from_file_location(
            "flowweaver_portable_runtime_audit",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _AUDIT = module
    return _AUDIT


def test_audit_accepts_minimal_embedded_runtime(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "checked"
    assert result.python_version == "3.12.10"
    assert result.pip_version == "26.1.2"
    assert result.errors == ()
    assert result.warnings == ()
    assert result.to_dict()["status"] == "checked"
    json.dumps(result.to_dict())


def test_audit_rejects_missing_python_exe(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)
    (portable_root / "EngineHost" / "python312" / "python.exe").unlink()

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "rejected"
    assert _issue_codes(result.errors) == {"python_exe_missing"}


def test_audit_rejects_disabled_import_site(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path, import_site=False)

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "rejected"
    assert _issue_codes(result.errors) == {"python_site_disabled"}


def test_audit_rejects_unsupported_python_version(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(python_version="Python 3.11.9"),
    )

    assert result.status == "rejected"
    assert _issue_codes(result.errors) == {"python_version_unsupported"}


def test_audit_rejects_runtime_token_database_and_logs(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)
    runtime_dir = portable_root / "EngineHost" / "runtime"
    (runtime_dir / "config").mkdir(parents=True)
    (runtime_dir / "metadata").mkdir()
    (runtime_dir / "logs").mkdir()
    (runtime_dir / "config" / "local_api_token").write_text(
        "secret",
        encoding="utf-8",
    )
    (runtime_dir / "metadata" / "flowweaver.db").write_text("", encoding="utf-8")
    (runtime_dir / "logs" / "enginehost.stdout.log").write_text("", encoding="utf-8")

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "rejected"
    assert "EngineHost/runtime/" in result.rejected_paths
    assert "EngineHost/runtime/config/local_api_token" in result.rejected_paths
    assert "EngineHost/runtime/metadata/flowweaver.db" in result.rejected_paths
    assert "EngineHost/runtime/logs/enginehost.stdout.log" in result.rejected_paths
    assert "rejected_path_present" in _issue_codes(result.errors)


def test_audit_records_cache_paths_as_excluded(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)
    package_dir = (
        portable_root / "EngineHost" / "python312" / "Lib" / "site-packages"
    )
    cache_dir = package_dir / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "module.cpython-312.pyc").write_text("", encoding="utf-8")

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "warning"
    assert (
        "EngineHost/python312/Lib/site-packages/__pycache__/"
        in result.excluded_paths
    )
    assert (
        "EngineHost/python312/Lib/site-packages/__pycache__/"
        "module.cpython-312.pyc"
        in result.excluded_paths
    )
    assert _issue_codes(result.warnings) == {"excluded_cache_paths_present"}


def test_audit_reports_dev_and_legacy_packages_as_warnings(
    tmp_path: Path,
) -> None:
    portable_root = _create_portable_root(
        tmp_path,
        packages={
            "pytest": "8.4.0",
            "PySide6_Addons": "6.9.0",
            "fastapi": "0.124.0",
        },
    )

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=_fake_command_runner(),
    )

    assert result.status == "warning"
    assert {package.name for package in result.packages} == {
        "fastapi",
        "pyside6-addons",
        "pytest",
    }
    assert _issue_codes(result.warnings) == {"dev_or_legacy_package_present"}
    assert len(result.warnings) == 2


def test_audit_warns_when_pip_version_is_unavailable(tmp_path: Path) -> None:
    portable_root = _create_portable_root(tmp_path)

    def command_runner(command: tuple[str, ...]) -> str:
        if command[1:] == ("--version",):
            return "Python 3.12.10"
        raise RuntimeError("pip missing")

    result = audit_module().audit_portable_runtime(
        portable_root,
        command_runner=command_runner,
    )

    assert result.status == "warning"
    assert result.python_version == "3.12.10"
    assert result.pip_version is None
    assert _issue_codes(result.warnings) == {"pip_version_unavailable"}


def _create_portable_root(
    tmp_path: Path,
    *,
    import_site: bool = True,
    include_license: bool = True,
    packages: dict[str, str] | None = None,
) -> Path:
    portable_root = tmp_path / "FlowWeaverPortable"
    python_dir = portable_root / "EngineHost" / "python312"
    site_packages = python_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    (python_dir / "python.exe").write_text("", encoding="utf-8")
    pth_lines = ["python312.zip", ".", "import site" if import_site else "#import site"]
    (python_dir / "python312._pth").write_text(
        "\n".join(pth_lines),
        encoding="utf-8",
    )
    if include_license:
        (python_dir / "LICENSE.txt").write_text("Python license", encoding="utf-8")
    for name, version in (packages or {}).items():
        (site_packages / f"{name}-{version}.dist-info").mkdir()
    return portable_root


def _fake_command_runner(
    *,
    python_version: str = "Python 3.12.10",
    pip_version: str = "pip 26.1.2 from fake (python 3.12)",
):
    def command_runner(command: tuple[str, ...]) -> str:
        if command[1:] == ("--version",):
            return python_version
        if command[1:] == ("-m", "pip", "--version"):
            return pip_version
        raise AssertionError(f"unexpected command: {command}")

    return command_runner


def _issue_codes(issues: tuple[object, ...]) -> set[str]:
    return {issue.code for issue in issues}

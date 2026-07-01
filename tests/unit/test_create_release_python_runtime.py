from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_MODULE = None


def runtime_module() -> ModuleType:
    global _MODULE
    if _MODULE is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "tools" / "create_release_python_runtime.py"
        spec = importlib.util.spec_from_file_location(
            "flowweaver_create_release_python_runtime",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def test_create_release_python_runtime_copies_independent_clean_runtime(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)
    output_dir = repo_root / ".tmp" / "FlowWeaverReleasePython312"
    commands: list[tuple[str, ...]] = []

    result = runtime_module().create_release_python_runtime(
        repo_root=repo_root,
        source_python_dir=source_python,
        output_dir=output_dir,
        command_runner=lambda command: commands.append(tuple(command)),
    )

    assert result.output_dir == output_dir.resolve()
    assert result.install_dependencies is True
    assert result.requirements == ("fastapi>=0.124.0", "uvicorn>=0.38.0")
    assert result.kept_tooling_packages == ("pip",)
    assert commands == [
        (
            str(output_dir.resolve() / "python.exe"),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--upgrade",
            "fastapi>=0.124.0",
            "uvicorn>=0.38.0",
        )
    ]

    output_site_packages = output_dir / "Lib" / "site-packages"
    assert (output_dir / "python.exe").is_file()
    assert (output_dir / "python312._pth").is_file()
    assert (output_dir / "LICENSE.txt").is_file()
    assert (output_site_packages / "pip").is_dir()
    assert (output_site_packages / "pip-26.1.2.dist-info").is_dir()
    assert not (output_site_packages / "pytest").exists()
    assert not (output_site_packages / "pytest-9.1.1.dist-info").exists()
    assert not (output_site_packages / "flowweaver").exists()
    assert not (output_site_packages / "__pycache__").exists()
    assert not any(output_dir.rglob("*.pyc"))

    source_site_packages = source_python / "Lib" / "site-packages"
    assert (source_site_packages / "pytest").is_dir()
    assert (source_site_packages / "flowweaver").is_dir()
    assert (source_site_packages / "__pycache__").is_dir()


def test_create_release_python_runtime_can_skip_dependency_install(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)
    commands: list[tuple[str, ...]] = []

    result = runtime_module().create_release_python_runtime(
        repo_root=repo_root,
        source_python_dir=source_python,
        output_dir=repo_root / ".tmp" / "ReleaseNoInstall",
        install_dependencies=False,
        command_runner=lambda command: commands.append(tuple(command)),
    )

    assert result.install_dependencies is False
    assert commands == []


def test_create_release_python_runtime_rejects_output_outside_tmp(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)

    with pytest.raises(
        runtime_module().ReleasePythonRuntimeError,
        match="output_dir must be inside",
    ):
        runtime_module().create_release_python_runtime(
            repo_root=repo_root,
            source_python_dir=source_python,
            output_dir=tmp_path / "outside",
        )


def test_create_release_python_runtime_parse_args_accepts_no_install() -> None:
    args = runtime_module().parse_args(["--no-install"])

    assert args.no_install is True


def _create_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".tmp").mkdir()
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "flowweaver"',
                'version = "0.1.0"',
                'dependencies = ["fastapi>=0.124.0", "uvicorn>=0.38.0"]',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return repo_root


def _create_source_python(repo_root: Path) -> Path:
    source_python = repo_root / "python312"
    site_packages = source_python / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    (source_python / "python.exe").write_text("", encoding="utf-8")
    (source_python / "LICENSE.txt").write_text("Python license", encoding="utf-8")
    (source_python / "python312._pth").write_text(
        "\n".join(["python312.zip", ".", "import site"]),
        encoding="utf-8",
    )
    _write_package(site_packages, "pip", "26.1.2")
    _write_package(site_packages, "pytest", "9.1.1")
    _write_package(site_packages, "flowweaver", "0.2.2")
    cache_dir = site_packages / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "module.cpython-312.pyc").write_text("", encoding="utf-8")
    return source_python


def _write_package(site_packages: Path, name: str, version: str) -> None:
    package_dir = site_packages / name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    dist_info_dir = site_packages / f"{name}-{version}.dist-info"
    dist_info_dir.mkdir()
    (dist_info_dir / "METADATA").write_text(
        "\n".join(
            [
                "Metadata-Version: 2.4",
                f"Name: {name}",
                f"Version: {version}",
                "",
            ]
        ),
        encoding="utf-8",
    )

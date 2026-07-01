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
    assert result.dependency_source == "pyproject"
    assert result.lock_file is None
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


def test_create_release_python_runtime_installs_from_locked_requirements(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)
    _write_uv_lock(repo_root / "uv.lock")
    output_dir = repo_root / ".tmp" / "LockedRelease"
    commands: list[tuple[str, ...]] = []
    requirement_files: list[str] = []

    def command_runner(command: tuple[str, ...]) -> None:
        commands.append(command)
        requirements_path = Path(command[-1])
        requirement_files.append(requirements_path.read_text(encoding="utf-8"))
        assert requirements_path.is_file()

    result = runtime_module().create_release_python_runtime(
        repo_root=repo_root,
        source_python_dir=source_python,
        output_dir=output_dir,
        dependency_source="lock",
        command_runner=command_runner,
    )

    assert result.dependency_source == "lock"
    assert result.lock_file == (repo_root / "uv.lock").resolve()
    assert result.requirements == (
        "click==8.4.2 --hash=sha256:click-wheel",
        "colorama==0.4.6 --hash=sha256:colorama-wheel",
        "fastapi==0.138.1 --hash=sha256:fastapi-wheel",
        "h11==0.16.0 --hash=sha256:h11-wheel",
        "uvicorn==0.49.0 --hash=sha256:uvicorn-wheel",
    )
    assert len(commands) == 1
    command = commands[0]
    assert command[:9] == (
        str(output_dir.resolve() / "python.exe"),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-warn-script-location",
        "--upgrade",
        "--require-hashes",
        "--only-binary=:all:",
    )
    assert command[-2] == "-r"
    requirements_path = Path(command[-1])
    assert not requirements_path.exists()

    assert len(requirement_files) == 1
    requirement_content = requirement_files[0]
    assert "fastapi==0.138.1 --hash=sha256:fastapi-wheel" in requirement_content
    assert "colorama==0.4.6 --hash=sha256:colorama-wheel" in requirement_content
    assert "pytest" not in requirement_content


def test_create_release_python_runtime_rejects_missing_lock_file(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)

    with pytest.raises(
        runtime_module().ReleasePythonRuntimeError,
        match="lock file missing",
    ):
        runtime_module().create_release_python_runtime(
            repo_root=repo_root,
            source_python_dir=source_python,
            output_dir=repo_root / ".tmp" / "MissingLock",
            dependency_source="lock",
        )


def test_create_release_python_runtime_rejects_lock_package_without_wheel_hash(
    tmp_path: Path,
) -> None:
    repo_root = _create_repo(tmp_path)
    source_python = _create_source_python(repo_root)
    _write_uv_lock(repo_root / "uv.lock", include_fastapi_wheel=False)

    with pytest.raises(
        runtime_module().ReleasePythonRuntimeError,
        match="has no wheel hashes",
    ):
        runtime_module().create_release_python_runtime(
            repo_root=repo_root,
            source_python_dir=source_python,
            output_dir=repo_root / ".tmp" / "MissingHash",
            dependency_source="lock",
        )


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


def test_create_release_python_runtime_parse_args_accepts_locked() -> None:
    args = runtime_module().parse_args(["--locked", "--lock-file", "custom.lock"])

    assert args.locked is True
    assert args.lock_file == Path("custom.lock")


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


def _write_uv_lock(path: Path, *, include_fastapi_wheel: bool = True) -> None:
    fastapi_wheels = (
        'wheels = [{ url = "fastapi.whl", hash = "sha256:fastapi-wheel" }]'
        if include_fastapi_wheel
        else "wheels = []"
    )
    path.write_text(
        "\n".join(
            [
                "version = 1",
                'requires-python = "==3.12.*"',
                "",
                "[[package]]",
                'name = "click"',
                'version = "8.4.2"',
                'wheels = [{ url = "click.whl", hash = "sha256:click-wheel" }]',
                "dependencies = [",
                '    { name = "colorama", marker = "sys_platform == \'win32\'" },',
                "]",
                "",
                "[[package]]",
                'name = "colorama"',
                'version = "0.4.6"',
                'wheels = [{ url = "colorama.whl", hash = "sha256:colorama-wheel" }]',
                "",
                "[[package]]",
                'name = "fastapi"',
                'version = "0.138.1"',
                fastapi_wheels,
                "",
                "[[package]]",
                'name = "flowweaver"',
                'version = "0.1.0"',
                'source = { editable = "." }',
                "dependencies = [",
                '    { name = "fastapi" },',
                '    { name = "uvicorn" },',
                "]",
                "",
                "[package.optional-dependencies]",
                "dev = [",
                '    { name = "pytest" },',
                "]",
                "",
                "[[package]]",
                'name = "h11"',
                'version = "0.16.0"',
                'wheels = [{ url = "h11.whl", hash = "sha256:h11-wheel" }]',
                "",
                "[[package]]",
                'name = "pytest"',
                'version = "9.1.1"',
                'wheels = [{ url = "pytest.whl", hash = "sha256:pytest-wheel" }]',
                "",
                "[[package]]",
                'name = "uvicorn"',
                'version = "0.49.0"',
                'wheels = [{ url = "uvicorn.whl", hash = "sha256:uvicorn-wheel" }]',
                "dependencies = [",
                '    { name = "click" },',
                '    { name = "h11" },',
                "]",
                "",
            ]
        ),
        encoding="utf-8",
    )


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

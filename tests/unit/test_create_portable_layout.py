from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_MODULE = None


def layout_module() -> ModuleType:
    global _MODULE
    if _MODULE is None:
        repo_root = Path(__file__).resolve().parents[2]
        module_path = repo_root / "tools" / "create_portable_layout.py"
        spec = importlib.util.spec_from_file_location(
            "flowweaver_create_portable_layout_unit",
            module_path,
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def test_create_portable_layout_can_copy_custom_python_runtime(
    tmp_path: Path,
) -> None:
    repo_root = _create_minimal_repo(tmp_path)
    release_runtime = tmp_path / "release-python312"
    (release_runtime / "Lib" / "site-packages").mkdir(parents=True)
    (release_runtime / "python.exe").write_text("release", encoding="utf-8")
    (release_runtime / "python312._pth").write_text("import site", encoding="utf-8")
    output_dir = repo_root / ".tmp" / "FlowWeaverPortable"

    portable_dir = layout_module().create_portable_layout(
        repo_root=repo_root,
        output_dir=output_dir,
        python_runtime_dir=release_runtime,
        include_python=True,
        include_desktop_build=False,
    )

    copied_python = portable_dir / "EngineHost" / "python312"
    assert (copied_python / "python.exe").read_text(encoding="utf-8") == "release"
    assert (copied_python / "python312._pth").read_text(encoding="utf-8") == (
        "import site"
    )


def _create_minimal_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".tmp").mkdir()
    (repo_root / "migrations").mkdir()
    (repo_root / "migrations" / "env.py").write_text("", encoding="utf-8")
    (repo_root / "src" / "flowweaver").mkdir(parents=True)
    (repo_root / "src" / "flowweaver" / "__init__.py").write_text(
        "",
        encoding="utf-8",
    )
    (repo_root / "tools").mkdir()
    (repo_root / "tools" / "portable_launcher.py").write_text("", encoding="utf-8")
    (repo_root / "docs").mkdir()
    (repo_root / "docs" / "FlowWeaver_便携版用户手册.md").write_text(
        "# FlowWeaver 便携版用户手册\n",
        encoding="utf-8",
    )
    for file_name in ("alembic.ini", "pyproject.toml", "uv.lock"):
        (repo_root / file_name).write_text("", encoding="utf-8")
    return repo_root

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType


def test_n6_desktop_publish_outputs_portable_desktop_files() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    publish_desktop = _load_publish_desktop(repo_root)
    output_dir = repo_root / ".tmp" / "FlowWeaverPortable" / "Desktop"
    shutil.rmtree(output_dir, ignore_errors=True)

    published_dir = publish_desktop(
        repo_root=repo_root,
        output_dir=output_dir,
        configuration="Release",
        runtime="win-x64",
        self_contained=False,
    )

    assert published_dir == output_dir.resolve()
    assert (output_dir / "Avalonia_UI.exe").is_file()
    assert (output_dir / "Avalonia_UI.dll").is_file()
    assert (output_dir / "Avalonia_UI.deps.json").is_file()
    assert (output_dir / "Avalonia_UI.runtimeconfig.json").is_file()

    published_names = {path.name for path in output_dir.iterdir()}
    assert "Avalonia.Diagnostics.dll" not in published_names
    assert any(
        name.startswith("Avalonia.") and name.endswith(".dll")
        for name in published_names
    )
    assert any(name.startswith("CommunityToolkit.Mvvm") for name in published_names)


def _load_publish_desktop(repo_root: Path):
    module_path = repo_root / "tools" / "publish_desktop.py"
    spec = importlib.util.spec_from_file_location(
        "flowweaver_publish_desktop",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {module_path}")
    module = importlib.util.module_from_spec(spec)
    assert isinstance(module, ModuleType)
    spec.loader.exec_module(module)
    return module.publish_desktop

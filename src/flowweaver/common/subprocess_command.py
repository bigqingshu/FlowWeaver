from __future__ import annotations

from pathlib import Path


def python_module_command(
    *,
    python_executable: str,
    module_name: str,
    src_path: Path,
) -> list[str]:
    bootstrap = (
        "import runpy, sys; "
        f"sys.path.insert(0, {str(src_path)!r}); "
        f"runpy.run_module({module_name!r}, run_name='__main__')"
    )
    return [python_executable, "-c", bootstrap]

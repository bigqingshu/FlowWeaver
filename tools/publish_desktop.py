from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "FlowWeaverPortable" / "Desktop"
PROJECT_PATH = REPO_ROOT / "Avalonia_UI" / "Avalonia_UI.csproj"


def publish_desktop(
    *,
    repo_root: Path = REPO_ROOT,
    output_dir: Path = DEFAULT_OUTPUT,
    configuration: str = "Release",
    runtime: str | None = "win-x64",
    self_contained: bool = False,
) -> Path:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    _validate_output_dir(repo_root=repo_root, output_dir=output_dir)
    project_path = repo_root / "Avalonia_UI" / "Avalonia_UI.csproj"
    if not project_path.is_file():
        raise FileNotFoundError(project_path)

    command = [
        "dotnet",
        "publish",
        str(project_path),
        "--configuration",
        configuration,
        "--output",
        str(output_dir),
        "--self-contained",
        str(self_contained).lower(),
    ]
    if runtime:
        command.extend(["--runtime", runtime])
    subprocess.run(command, cwd=repo_root, check=True)
    return output_dir


def _validate_output_dir(*, repo_root: Path, output_dir: Path) -> None:
    tmp_root = (repo_root / ".tmp").resolve()
    if output_dir != tmp_root and tmp_root in output_dir.parents:
        return
    raise ValueError(f"output_dir must be a child directory inside {tmp_root}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the Avalonia desktop app into a portable layout."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory. Must be inside repo .tmp/.",
    )
    parser.add_argument(
        "--configuration",
        default="Release",
        help="dotnet publish configuration.",
    )
    parser.add_argument(
        "--runtime",
        default="win-x64",
        help="dotnet publish runtime identifier. Use empty string to omit.",
    )
    parser.add_argument(
        "--self-contained",
        action="store_true",
        help="Publish as self-contained.",
    )
    args = parser.parse_args()
    runtime = args.runtime if args.runtime else None
    output_dir = publish_desktop(
        output_dir=args.output,
        configuration=args.configuration,
        runtime=runtime,
        self_contained=args.self_contained,
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path


def batch_rename_target_path(
    source_path: Path,
    new_name: str,
    *,
    name_value_type: str,
    auto_append_ext: bool,
) -> Path:
    if name_value_type == "full_path":
        target_path = Path(new_name).expanduser()
    else:
        target_path = source_path.with_name(new_name)
    if auto_append_ext and source_path.suffix and not target_path.suffix:
        target_path = target_path.with_suffix(source_path.suffix)
    return target_path


def batch_rename_append_number_path(target_path: Path) -> Path:
    if not target_path.exists():
        return target_path
    index = 2
    while True:
        candidate = target_path.with_name(
            f"{target_path.stem}_{index}{target_path.suffix}"
        )
        if not candidate.exists():
            return candidate
        index += 1


def batch_rename_execute(
    *,
    source_path: Path,
    target_path: Path,
    create_target_dirs: bool,
    conflict_mode: str,
) -> tuple[str, str, str, bool]:
    try:
        if create_target_dirs:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            if conflict_mode == "skip":
                return (
                    "skipped",
                    "",
                    "target path already exists",
                    False,
                )
            if conflict_mode == "error":
                return (
                    "failed",
                    "target path already exists",
                    "",
                    False,
                )
            if conflict_mode == "append_number":
                target_path = batch_rename_append_number_path(target_path)
        source_path.replace(target_path)
        return ("renamed", "", "", True)
    except OSError as exc:
        return ("failed", str(exc), "", False)

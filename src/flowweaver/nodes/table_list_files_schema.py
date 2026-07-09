from __future__ import annotations

from flowweaver.nodes.table_node_common import simple_schema as _simple_schema
from flowweaver.protocols.table_ref import FieldSchemaModel


def list_files_schema() -> list[FieldSchemaModel]:
    return _simple_schema(
        [
            ("name", "TEXT", False),
            ("path", "TEXT", False),
            ("parent_path", "TEXT", False),
            ("relative_path", "TEXT", False),
            ("extension", "TEXT", False),
            ("stem", "TEXT", False),
            ("is_dir", "TEXT", False),
            ("is_file", "TEXT", False),
            ("is_symlink", "TEXT", False),
            ("size_bytes", "INTEGER", True),
            ("modified_at", "TEXT", True),
        ]
    )

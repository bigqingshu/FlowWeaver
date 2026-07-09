from __future__ import annotations

from flowweaver.nodes.registry import NodeConfigFieldSpec, NodeConfigSchemaSpec


def _list_files_schema() -> NodeConfigSchemaSpec:
    return NodeConfigSchemaSpec(
        properties={
            "directory": NodeConfigFieldSpec(
                type="string",
                title="Directory",
                required=True,
            ),
            "recursive": NodeConfigFieldSpec(
                type="boolean",
                title="Recursive",
                default=False,
            ),
            "include_files": NodeConfigFieldSpec(
                type="boolean",
                title="Include Files",
                default=True,
            ),
            "include_dirs": NodeConfigFieldSpec(
                type="boolean",
                title="Include Directories",
                default=False,
            ),
            "include_hidden": NodeConfigFieldSpec(
                type="boolean",
                title="Include Hidden",
                default=False,
            ),
            "extensions": NodeConfigFieldSpec(
                type="array",
                title="Extensions",
                item_type="string",
                description="Optional file extensions, with or without leading dots.",
            ),
            "name_contains": NodeConfigFieldSpec(
                type="string",
                title="Name Contains",
                default="",
            ),
            "glob_pattern": NodeConfigFieldSpec(
                type="string",
                title="Glob Pattern",
                default="*",
            ),
            "max_files": NodeConfigFieldSpec(
                type="integer",
                title="Max Files",
                default=10000,
                minimum=1,
            ),
        }
    )

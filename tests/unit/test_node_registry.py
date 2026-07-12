from flowweaver.nodes.default_registry import default_node_definitions
from flowweaver.nodes.registry import (
    NodeConfigFieldSpec,
    NodeConfigSchemaSpec,
    NodeDefinitionSpec,
    NodePortSpec,
    NodeRegistry,
    NodeTableInputSlotSpec,
    NodeTableOutputSlotSpec,
)
from flowweaver.protocols.enums import TableRole, TableStorageKind


def test_catalog_state_is_stable_for_same_visible_definitions() -> None:
    registry = NodeRegistry()
    registry.register(_definition())

    first = registry.catalog_state()
    second = registry.catalog_state()

    assert first == second
    assert first.node_count == 1
    assert len(first.catalog_hash) == 64


def test_catalog_state_excludes_hidden_node_types_from_hash() -> None:
    first_registry = NodeRegistry()
    first_registry.register(_definition())
    first_registry.register(
        _definition(node_type="HiddenNode", display_name="Hidden A")
    )

    second_registry = NodeRegistry()
    second_registry.register(_definition())
    second_registry.register(
        _definition(node_type="HiddenNode", display_name="Hidden B")
    )

    first = first_registry.catalog_state(excluded_node_types={"HiddenNode"})
    second = second_registry.catalog_state(excluded_node_types={"HiddenNode"})

    assert first == second
    assert first.node_count == 1


def test_catalog_state_changes_when_visible_schema_changes() -> None:
    first_registry = NodeRegistry()
    first_registry.register(_definition(field_title="First"))

    second_registry = NodeRegistry()
    second_registry.register(_definition(field_title="Second"))

    assert first_registry.catalog_state().catalog_hash != (
        second_registry.catalog_state().catalog_hash
    )


def test_definition_catalog_data_includes_table_slots() -> None:
    definition = NodeDefinitionSpec(
        node_type="SlotNode",
        node_version="1.0",
        display_name="Slot Node",
        input_table_slots=(
            NodeTableInputSlotSpec(
                name="main_table",
                display_name="Main table",
                description="Primary input table.",
                required=True,
                allowed_storage_kinds=(
                    TableStorageKind.RUNTIME_SQL,
                    TableStorageKind.MEMORY,
                ),
            ),
        ),
        output_table_slots=(
            NodeTableOutputSlotSpec(
                name="result_table",
                display_name="Result table",
                description="Primary output table.",
                default_role=TableRole.AUXILIARY,
                allow_current=False,
                allow_new_runtime_sql=True,
                allow_existing_runtime_sql=True,
            ),
        ),
    )

    catalog_data = definition.to_catalog_data()

    assert catalog_data["plugin_id"] == "flowweaver.core"
    assert catalog_data["provider_type"] == "core"
    assert catalog_data["ui_visibility"] == "visible"
    assert catalog_data["enabled"] is True
    assert "implementation_ref" not in catalog_data

    assert catalog_data["input_table_slots"] == [
        {
            "name": "main_table",
            "required": True,
            "allowed_storage_kinds": ["RUNTIME_SQL", "MEMORY"],
            "display_name": "Main table",
            "description": "Primary input table.",
            "default_source": "upstream_current",
        }
    ]
    assert catalog_data["output_table_slots"] == [
        {
            "name": "result_table",
            "default_role": "AUXILIARY",
            "allow_current": False,
            "allow_new_memory": False,
            "allow_new_runtime_sql": True,
            "allow_existing_memory": False,
            "allow_existing_runtime_sql": True,
            "display_name": "Result table",
            "description": "Primary output table.",
        }
    ]


def test_catalog_state_changes_when_visible_table_slots_change() -> None:
    first_registry = NodeRegistry()
    first_registry.register(
        _definition(
            input_table_slots=(
                NodeTableInputSlotSpec(
                    name="main_table",
                    display_name="Main table",
                ),
            ),
        )
    )

    second_registry = NodeRegistry()
    second_registry.register(
        _definition(
            input_table_slots=(
                NodeTableInputSlotSpec(
                    name="rules_table",
                    display_name="Rules table",
                ),
            ),
        )
    )

    assert first_registry.catalog_state().catalog_hash != (
        second_registry.catalog_state().catalog_hash
    )


def test_catalog_state_filters_by_ui_visibility() -> None:
    node_registry = NodeRegistry()
    node_registry.register(_definition())
    node_registry.register(
        NodeDefinitionSpec(
            node_type="HiddenNode",
            node_version="1.0",
            display_name="Hidden",
            ui_visibility="hidden",
        )
    )

    state = node_registry.catalog_state(ui_visibilities={"visible"})

    assert state.node_count == 1


def test_default_builtin_node_baseline_remains_41() -> None:
    assert len(default_node_definitions()) == 41


def _definition(
    *,
    node_type: str = "ExampleNode",
    display_name: str = "Example",
    field_title: str = "Value",
    input_table_slots: tuple[NodeTableInputSlotSpec, ...] = (),
    output_table_slots: tuple[NodeTableOutputSlotSpec, ...] = (),
) -> NodeDefinitionSpec:
    return NodeDefinitionSpec(
        node_type=node_type,
        node_version="1.0",
        display_name=display_name,
        input_ports=(NodePortSpec("in", required=True),),
        output_ports=(NodePortSpec("out"),),
        input_table_slots=input_table_slots,
        output_table_slots=output_table_slots,
        config_schema=NodeConfigSchemaSpec(
            properties={
                "value": NodeConfigFieldSpec(
                    type="string",
                    title=field_title,
                    required=True,
                ),
            },
        ),
    )

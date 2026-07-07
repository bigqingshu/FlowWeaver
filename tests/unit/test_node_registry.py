from flowweaver.nodes.registry import (
    NodeConfigFieldSpec,
    NodeConfigSchemaSpec,
    NodeDefinitionSpec,
    NodePortSpec,
    NodeRegistry,
)


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


def _definition(
    *,
    node_type: str = "ExampleNode",
    display_name: str = "Example",
    field_title: str = "Value",
) -> NodeDefinitionSpec:
    return NodeDefinitionSpec(
        node_type=node_type,
        node_version="1.0",
        display_name=display_name,
        input_ports=(NodePortSpec("in", required=True),),
        output_ports=(NodePortSpec("out"),),
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
